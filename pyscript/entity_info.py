import json
import time

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr

SCHEMA_ID = "snailicide.entity_info.v2"
SCHEMA_VERSION = 2

BINARY_DOMAINS = {"light", "switch", "binary_sensor", "input_boolean"}

log.info("Loaded entity_info.py (response-data version with area/device/label support)")


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


def _as_str_list(x):
    if x is None:
        return []
    if isinstance(x, str):
        s = x.strip()
        if s:
            return [s]
        return []
    if isinstance(x, (list, tuple)):
        out = []
        for item in x:
            if isinstance(item, str):
                s = item.strip()
                if s:
                    out.append(s)
        return out
    return []


def _as_entities(x):
    out = []
    for value in _as_str_list(x):
        if _is_entity_id(value):
            out.append(value)
    return out


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


def _parse_args(entities, areas, devices, labels, flatten_members, dedupe, request_id):
    ents = _as_entities(entities)
    ars = _as_str_list(areas)
    devs = _as_str_list(devices)
    lbls = _as_str_list(labels)
    flat = _as_bool(flatten_members, False)
    ddp = _as_bool(dedupe, True)
    rid = _as_request_id(request_id)
    return ents, ars, devs, lbls, flat, ddp, rid


def _is_entity_id(x):
    if not isinstance(x, str):
        return False
    if "." not in x:
        return False
    parts = x.split(".", 1)
    return bool(parts[0]) and bool(parts[1])


def _add_unique_str(out, seen, value):
    if not isinstance(value, str):
        return False
    if not value:
        return False
    if value in seen:
        return False
    out.append(value)
    seen.add(value)
    return True


# -----------------------------
# Registry helpers
# -----------------------------


def _resolve_area_ids(area_values, areg, errors):
    out = []
    seen = set()

    for value in area_values:
        area = areg.async_get_area(value)
        if area is None and hasattr(areg, "async_get_area_by_name"):
            try:
                area = areg.async_get_area_by_name(value)
            except Exception:
                area = None

        if area is None:
            errors.append(
                {
                    "code": "BAD_AREA",
                    "message": "Unknown area: %r" % (value,),
                    "entity_id": None,
                }
            )
            continue

        _add_unique_str(out, seen, area.id)

    return out


def _resolve_device_ids(device_values, dreg, errors):
    out = []
    seen = set()

    for value in device_values:
        device = dreg.async_get(value)
        if device is None:
            errors.append(
                {
                    "code": "BAD_DEVICE",
                    "message": "Unknown device_id: %r" % (value,),
                    "entity_id": None,
                }
            )
            continue

        _add_unique_str(out, seen, value)

    return out


def _resolve_label_ids(label_values, lreg, errors):
    out = []
    seen = set()

    for value in label_values:
        label = None

        if hasattr(lreg, "async_get_label"):
            try:
                label = lreg.async_get_label(value)
            except Exception:
                label = None

        if label is None and hasattr(lreg, "async_get_label_by_name"):
            try:
                label = lreg.async_get_label_by_name(value)
            except Exception:
                label = None

        if label is None:
            errors.append(
                {
                    "code": "BAD_LABEL",
                    "message": "Unknown label: %r" % (value,),
                    "entity_id": None,
                }
            )
            continue

        label_id = getattr(label, "label_id", None) or getattr(label, "id", None)
        if not isinstance(label_id, str):
            errors.append(
                {
                    "code": "BAD_LABEL",
                    "message": "Label did not provide a usable ID: %r" % (value,),
                    "entity_id": None,
                }
            )
            continue

        _add_unique_str(out, seen, label_id)

    return out


def _collect_entity_ids_from_devices(device_ids, ereg):
    out = []
    seen = set()

    for device_id in device_ids:
        try:
            entries = er.async_entries_for_device(ereg, device_id)
        except Exception:
            entries = []

        for entry in entries:
            entity_id = getattr(entry, "entity_id", None)
            _add_unique_str(out, seen, entity_id)

    return out


def _collect_entity_ids_from_areas(area_ids, dreg, ereg):
    out = []
    seen = set()

    for area_id in area_ids:
        try:
            entity_entries = er.async_entries_for_area(ereg, area_id)
        except Exception:
            entity_entries = []

        for entry in entity_entries:
            entity_id = getattr(entry, "entity_id", None)
            _add_unique_str(out, seen, entity_id)

        try:
            device_entries = dr.async_entries_for_area(dreg, area_id)
        except Exception:
            device_entries = []

        for device in device_entries:
            device_id = getattr(device, "id", None)
            if not isinstance(device_id, str):
                continue

            try:
                child_entries = er.async_entries_for_device(ereg, device_id)
            except Exception:
                child_entries = []

            for entry in child_entries:
                entity_id = getattr(entry, "entity_id", None)
                _add_unique_str(out, seen, entity_id)

    return out


def _collect_entity_ids_from_labels(label_ids, areg, dreg, ereg):
    out = []
    seen = set()

    for label_id in label_ids:
        try:
            entity_entries = er.async_entries_for_label(ereg, label_id)
        except Exception:
            entity_entries = []

        for entry in entity_entries:
            entity_id = getattr(entry, "entity_id", None)
            _add_unique_str(out, seen, entity_id)

        try:
            device_entries = dr.async_entries_for_label(dreg, label_id)
        except Exception:
            device_entries = []

        for device in device_entries:
            device_id = getattr(device, "id", None)
            if not isinstance(device_id, str):
                continue

            try:
                child_entries = er.async_entries_for_device(ereg, device_id)
            except Exception:
                child_entries = []

            for entry in child_entries:
                entity_id = getattr(entry, "entity_id", None)
                _add_unique_str(out, seen, entity_id)

        try:
            area_entries = ar.async_entries_for_label(areg, label_id)
        except Exception:
            area_entries = []

        for area in area_entries:
            area_id = getattr(area, "id", None)
            if not isinstance(area_id, str):
                continue

            for entity_id in _collect_entity_ids_from_areas([area_id], dreg, ereg):
                _add_unique_str(out, seen, entity_id)

    return out


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


def _labels_from_entry(entry):
    try:
        labels = getattr(entry, "labels", None)
        if labels is None:
            return []
        out = []
        for value in labels:
            out.append(value)
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
        "device_labels": _labels_from_entry(device) if device else [],
        "entity_labels": _labels_from_entry(entry) if entry else [],
        "area_id": area_id,
        "area_name": area_name,
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
            base["device_labels"] = group_entities[0].get("device_labels")
        if (not base.get("area_id")) and group_entities:
            base["area_id"] = group_entities[0].get("area_id")
            base["area_name"] = group_entities[0].get("area_name")

    base["group_entities"] = group_entities
    return base


# -----------------------------
# Service (response data)
# -----------------------------


@service("pyscript.entity_info", supports_response="only")
def entity_info(
    entities=None,
    areas=None,
    devices=None,
    labels=None,
    flatten_members=False,
    dedupe=True,
    request_id=None,
):
    """yaml
    name: Entity Info
    description: Fetch metadata for one or more Home Assistant entities, areas, devices, or labels, with optional group expansion.

    fields:
      entities:
        name: Entities
        description: One or more entities to inspect directly.
        example: light.kitchen
        selector:
          entity:
            multiple: true

      areas:
        name: Areas
        description: One or more areas. Entities from these areas will be included.
        selector:
          area:
            multiple: true

      devices:
        name: Devices
        description: One or more devices. Entities from these devices will be included.
        selector:
          device:
            multiple: true

      labels:
        name: Labels
        description: Select one or more labels. Matching labeled entities, devices, and areas will be expanded to entities.
        selector:
          label:
            multiple: true

      flatten_members:
        name: Flatten group members
        description: Include group members as top-level items in the returned response.
        default: false
        selector:
          boolean:

      dedupe:
        name: Dedupe flattened members
        description: When flattening, avoid returning duplicate entity IDs.
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
    """
    ents, area_values, device_values, label_values, flat, ddp, rid = _parse_args(
        entities,
        areas,
        devices,
        labels,
        flatten_members,
        dedupe,
        request_id,
    )
    log.info(
        "entity_info: entities=%r areas=%r devices=%r labels=%r flatten_members=%r dedupe=%r request_id=%r"
        % (ents, area_values, device_values, label_values, flat, ddp, rid)
    )

    dreg = dr.async_get(hass)
    ereg = er.async_get(hass)
    areg = ar.async_get(hass)
    lreg = lr.async_get(hass)

    errors = []
    items = []

    area_ids = _resolve_area_ids(area_values, areg, errors)
    device_ids = _resolve_device_ids(device_values, dreg, errors)
    label_ids = _resolve_label_ids(label_values, lreg, errors)

    candidate_entity_ids = []
    seen_candidate_entity_ids = set()

    for entity_id in ents:
        _add_unique_str(candidate_entity_ids, seen_candidate_entity_ids, entity_id)

    for entity_id in _collect_entity_ids_from_areas(area_ids, dreg, ereg):
        _add_unique_str(candidate_entity_ids, seen_candidate_entity_ids, entity_id)

    for entity_id in _collect_entity_ids_from_devices(device_ids, ereg):
        _add_unique_str(candidate_entity_ids, seen_candidate_entity_ids, entity_id)

    for entity_id in _collect_entity_ids_from_labels(label_ids, areg, dreg, ereg):
        _add_unique_str(candidate_entity_ids, seen_candidate_entity_ids, entity_id)

    for e in candidate_entity_ids:
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
    # root_group_count = number of top-level returned entities that are groups (not including children)
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

    return {
        "schema_id": SCHEMA_ID,
        "version": SCHEMA_VERSION,
        "request_id": rid,
        "meta": {
            "count": len(items),
            "entity_input_count": len(ents),
            "area_input_count": len(area_values),
            "device_input_count": len(device_values),
            "label_input_count": len(label_values),
            "resolved_area_count": len(area_ids),
            "resolved_device_count": len(device_ids),
            "resolved_label_count": len(label_ids),
            "candidate_entity_count": len(candidate_entity_ids),
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
    }
