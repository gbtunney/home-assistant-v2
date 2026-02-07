"""
entity_info PyScript service

Service: pyscript.entity_info
Emits event: entity_info_list_return

Notes:
- PyScript has limited AST support. Avoid generator expressions, comprehensions,
  and typing-heavy constructs.
- Services do not return values; this service emits an event with the payload.
"""

import json

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import area_registry as ar

EVENT_TYPE = "entity_info_list_return"
SCHEMA_ID = "snailicide.entity_info.v1"
SCHEMA_VERSION = 1

BINARY_DOMAINS = {"light", "switch", "binary_sensor", "input_boolean"}

log.info("Loaded entity_info.py (rewrite: no generators/comprehensions)")


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


def _as_request_id(x):
    if x is None:
        return None
    try:
        s = str(x).strip()
        if s:
            return s
        return None
    except Exception:
        return None


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
        # labels is iterable-ish; normalize to list of strings
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

    group_entities = []
    if is_group:
        for m in valid_members:
            # skip stale members
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

        # Inherit device/area from first usable child if parent lacks it
        if (not base.get("device_id")) and group_entities:
            base["device_id"] = group_entities[0].get("device_id")
            base["device_name"] = group_entities[0].get("device_name")
        if (not base.get("area_id")) and group_entities:
            base["area_id"] = group_entities[0].get("area_id")
            base["area_name"] = group_entities[0].get("area_name")

    base["group_entities"] = group_entities
    return base


# -----------------------------
# Service
# -----------------------------


@service("pyscript.entity_info")
def entity_info(entities=None, flatten_members=False, dedupe=True, request_id=None):
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

    # Flatten group members into top-level list
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

            items = flat_items
        except Exception as ex:
            errors.append(
                {"code": "FLATTEN_FAILED", "message": str(ex), "entity_id": None}
            )

    # Serialize items_json
    try:
        items_json = json.dumps(items)
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

    payload = {
        "schema_id": SCHEMA_ID,
        "version": SCHEMA_VERSION,
        "request_id": rid,
        "meta": {
            "count": len(items),
            "input_count": len(ents),
            "flatten_members": flat,
            "dedupe": ddp,
        },
        "errors": errors,
        "items": items,
        "items_json": items_json,
    }

    event.fire(EVENT_TYPE, **payload)
    log.info("entity_info: returned %d items; errors=%d" % (len(items), len(errors)))
