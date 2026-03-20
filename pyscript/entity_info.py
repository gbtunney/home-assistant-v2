import json
import time

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import area_registry as ar

SCHEMA_ID = "snailicide.entity_info.v1"
SCHEMA_VERSION = 1

BINARY_DOMAINS = {"light", "switch", "binary_sensor", "input_boolean"}

log.info("Loaded entity_info.py (response-data version)")


# -----------------------------
# Input coercion / validation
# -----------------------------


def _as_bool(x, default=False):
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        return x.strip().lower() in ("1", "true", "yes", "on")
    if x is None:
        return default
    return bool(x)


def _as_entities(x):
    if x is None:
        return []
    if isinstance(x, str):
        return [x]
    if isinstance(x, (list, tuple)):
        out = []
        for e in x:
            if isinstance(e, str):
                out.append(e)
        return out
    return []


def _make_request_id():
    try:
        return "entity-info-%d" % int(time.time() * 1000)
    except Exception:
        return "entity-info-auto"


def _as_request_id(x):
    if x is None:
        return _make_request_id()
    try:
        s = str(x).strip()
        if s:
            return s
        return _make_request_id()
    except Exception:
        return _make_request_id()


def _parse_args(entities, flatten_members, dedupe, request_id):
    ents = _as_entities(entities)
    flat = _as_bool(flatten_members, False)
    ddp = _as_bool(dedupe, True)
    rid = _as_request_id(request_id)
    return ents, flat, ddp, rid


def _is_entity_id(x):
    if not isinstance(x, str):
        return False
    if "." not in x:
        return False
    parts = x.split(".", 1)
    return bool(parts[0]) and bool(parts[1])


# -----------------------------
# Core extraction
# -----------------------------


def _norm_state(hass, entity_id, domain):
    st = hass.states.get(entity_id)
    raw = st.state if st else "unknown"

    if domain in BINARY_DOMAINS:
        if raw in ("on", "off", "unavailable", "unknown"):
            return raw, "binary", None
        return "unknown", "binary", None

    try:
        num = float(raw)
        return raw, "number", num
    except (ValueError, TypeError):
        return raw, "text", None


def _labels_from_device(device):
    try:
        lbl = getattr(device, "labels", None)
        if lbl is None:
            return []
        out = []
        try:
            for v in lbl:
                out.append(v)
        except Exception:
            return []
        return out
    except Exception:
        return []


def _core_entity(hass, entity_id, dreg, ereg, areg):
    entry = ereg.async_get(entity_id)
    dev_id = entry.device_id if entry else None
    device = dreg.async_get(dev_id) if dev_id else None

    domain = entity_id.split(".", 1)[0]
    st = hass.states.get(entity_id)

    name = entity_id
    if st:
        fn = st.attributes.get("friendly_name")
        if isinstance(fn, str) and fn:
            name = fn

    area_id = None
    if device and getattr(device, "area_id", None):
        area_id = device.area_id
    elif entry and getattr(entry, "area_id", None):
        area_id = entry.area_id

    area_name = None
    if area_id:
        area = areg.async_get_area(area_id)
        if area:
            area_name = area.name

    device_name = None
    if device:
        device_name = device.name or device.model

    labels = _labels_from_device(device) if device else []

    state, state_kind, state_number = _norm_state(hass, entity_id, domain)

    return {
        "entity_id": entity_id,
        "domain": domain,
        "name": name,
        "state": state,
        "state_kind": state_kind,
        "state_number": state_number,
        "device_id": dev_id,
        "device_name": device_name,
        "area_id": area_id,
        "area_name": area_name,
        "labels": labels,
    }


def _build_entry(hass, entity_id, dreg, ereg, areg, errors):
    base = _core_entity(hass, entity_id, dreg, ereg, areg)

    group_members = []
    st = hass.states.get(entity_id)
    if st:
        members = st.attributes.get("entity_id", [])
        if isinstance(members, (list, tuple)):
            group_members = list(members)

    valid_members = []
    for m in group_members:
        if not _is_entity_id(m):
            if m is not None:
                errors.append(
                    {
                        "code": "BAD_GROUP_MEMBER",
                        "message": "Non-entity member: %r" % (m,),
                        "entity_id": entity_id,
                    }
                )
            continue
        valid_members.append(m)

    is_group = len(valid_members) > 0
    base["group"] = is_group
    base["group_member_count"] = len(valid_members)

    group_entities = []
    if is_group:
        for m in valid_members:
            if hass.states.get(m) is None and ereg.async_get(m) is None:
                errors.append(
                    {
                        "code": "MISSING_MEMBER",
                        "message": "Member not found in state/registry",
                        "entity_id": m,
                    }
                )
                continue
            try:
                group_entities.append(_core_entity(hass, m, dreg, ereg, areg))
            except Exception as ex:
                errors.append(
                    {
                        "code": "CHILD_BUILD_FAILED",
                        "message": str(ex),
                        "entity_id": m,
                    }
                )

        if (not base.get("device_id")) and group_entities:
            base["device_id"] = group_entities[0].get("device_id")
            base["device_name"] = group_entities[0].get("device_name")
        if (not base.get("area_id")) and group_entities:
            base["area_id"] = group_entities[0].get("area_id")
            base["area_name"] = group_entities[0].get("area_name")

    base["group_entities"] = group_entities
    return base


# -----------------------------
# Service (response data)
# -----------------------------


@service("pyscript.entity_info", supports_response="only")
def entity_info(entities=None, flatten_members=False, dedupe=True, request_id=None):
    """yaml
    name: Entity Info
    description: Fetch metadata for one or more Home Assistant entities, including device, area, state, and optional group expansion.

    fields:
      entities:
        name: Entities
        description: One or more entities to inspect.
        required: false
        example: light.kitchen
        selector:
          entity:
            multiple: true

      flatten_members:
        name: Flatten group members
        description: Include group members as top-level items in the returned response.
        required: false
        default: false
        selector:
          boolean:

      dedupe:
        name: Dedupe flattened members
        description: When flattening, avoid returning duplicate entity IDs.
        required: false
        default: true
        selector:
          boolean:

      request_id:
        name: Request ID
        description: Optional label for this request. If omitted, one is generated automatically and echoed in the response.
        example: kitchen-check
        selector:
          text:

    response:
      schema_id:
        description: Stable schema identifier
      version:
        description: Schema version
      request_id:
        description: Provided or auto-generated request identifier
      meta:
        description: Summary metadata about the result set
      errors:
        description: Any validation or processing errors
      items:
        description: Structured entity info records
      items_json:
        description: JSON string of items for templating
      items_json_pretty:
        description: Pretty-printed JSON string of items for easier reading
    """
    ents, flat, ddp, rid = _parse_args(entities, flatten_members, dedupe, request_id)
    log.info(
        "entity_info: entities=%r flatten_members=%r dedupe=%r request_id=%r"
        % (ents, flat, ddp, rid)
    )

    dreg = dr.async_get(hass)
    ereg = er.async_get(hass)
    areg = ar.async_get(hass)

    errors = []
    items = []

    for e in ents:
        if not _is_entity_id(e):
            errors.append(
                {
                    "code": "BAD_ENTITY_ID",
                    "message": "Not a valid entity_id: %r" % (e,),
                    "entity_id": None,
                }
            )
            continue
        try:
            items.append(_build_entry(hass, e, dreg, ereg, areg, errors))
        except Exception as ex:
            errors.append(
                {
                    "code": "ENTRY_BUILD_FAILED",
                    "message": str(ex),
                    "entity_id": e,
                }
            )

    root_count = len(items)
    # root_group_count = number of top-level requested entities that are groups (not including children)
    root_group_count = 0
    child_count = 0
    for entry in items:
        if isinstance(entry, dict):
            if bool(entry.get("group", False)):
                root_group_count += 1
            children = entry.get("group_entities")
            if isinstance(children, list):
                child_count += len(children)

    flattened_added_count = 0
    deduped_skipped_count = 0

    if flat:
        try:
            flat_items = []
            for it in items:
                flat_items.append(it)

            seen = set()
            for it in flat_items:
                if isinstance(it, dict):
                    eid = it.get("entity_id")
                    if isinstance(eid, str):
                        seen.add(eid)

            for entry in items:
                if not isinstance(entry, dict):
                    continue
                children = entry.get("group_entities")
                if not isinstance(children, list):
                    continue

                for child in children:
                    if not isinstance(child, dict):
                        continue
                    eid = child.get("entity_id")
                    if not isinstance(eid, str):
                        continue

                    if (not ddp) or (eid not in seen):
                        flat_items.append(child)
                        seen.add(eid)
                        flattened_added_count += 1
                    else:
                        deduped_skipped_count += 1

            items = flat_items
        except Exception as ex:
            errors.append(
                {"code": "FLATTEN_FAILED", "message": str(ex), "entity_id": None}
            )

    try:
        items_json = json.dumps(items)
        items_json_pretty = json.dumps(items, indent=2, sort_keys=True)
    except Exception as ex:
        errors.append(
            {"code": "JSON_DUMPS_FAILED", "message": str(ex), "entity_id": None}
        )
        fallback = []
        for it in items:
            if isinstance(it, dict):
                fallback.append(
                    {"entity_id": it.get("entity_id"), "error": "json_failed"}
                )
            else:
                fallback.append({"entity_id": None, "error": "json_failed"})
        items_json = json.dumps(fallback)
        items_json_pretty = json.dumps(fallback, indent=2, sort_keys=True)

    return {
        "schema_id": SCHEMA_ID,
        "version": SCHEMA_VERSION,
        "request_id": rid,
        "meta": {
            "count": len(items),
            "input_count": len(ents),
            "root_count": root_count,
            "root_group_count": root_group_count,
            "child_count": child_count,
            "flatten_members": flat,
            "flattened_added_count": flattened_added_count,
            "returned_count": len(items),
            "dedupe": ddp,
            "deduped_skipped_count": deduped_skipped_count,
        },
        "errors": errors,
        "items": items,
        "items_json": items_json,
        "items_json_pretty": items_json_pretty,
    }
