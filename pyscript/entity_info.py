"""
entity_info PyScript service

Service: pyscript.entity_info
Emits event: entity_info_list_return
"""

import json

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import area_registry as ar

EVENT_TYPE = "entity_info_list_return"
SCHEMA_ID = "snailicide.entity_info.v1"
SCHEMA_VERSION = 1

BINARY_DOMAINS = {"light", "switch", "binary_sensor", "input_boolean"}

log.info("Loaded entity_info.py")


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
        return [e for e in x if isinstance(e, str)]
    return []


def _parse_args(entities, flatten_members, dedupe, request_id):
    ents = _as_entities(entities)
    flat = _as_bool(flatten_members, False)
    ddp = _as_bool(dedupe, True)
    rid = request_id if isinstance(request_id, str) and request_id.strip() else None
    return ents, flat, ddp, rid


def _is_entity_id(x):
    return isinstance(x, str) and "." in x and x.split(".", 1)[0] and x.split(".", 1)[1]


# -----------------------------
# Core extraction
# -----------------------------


def _norm_state(hass, entity_id, domain):
    st = hass.states.get(entity_id)
    raw = st.state if st else "unknown"

    if domain in BINARY_DOMAINS:
        normalized = (
            raw if raw in ("on", "off", "unavailable", "unknown") else "unknown"
        )
        return normalized, "binary", None

    try:
        num = float(raw)
        return raw, "number", num
    except (ValueError, TypeError):
        return raw, "text", None


def _labels_from_device(device):
    try:
        lbl = getattr(device, "labels", []) or []
        return list(lbl) if hasattr(lbl, "__iter__") else []
    except Exception:
        return []


def _core_entity(hass, entity_id, dreg, ereg, areg):
    entry = ereg.async_get(entity_id)
    dev_id = entry.device_id if entry else None
    device = dreg.async_get(dev_id) if dev_id else None

    domain = entity_id.split(".", 1)[0]
    st = hass.states.get(entity_id)
    name = (st.attributes.get("friendly_name") if st else None) or entity_id

    area_id = None
    if device and getattr(device, "area_id", None):
        area_id = device.area_id
    elif entry and getattr(entry, "area_id", None):
        area_id = entry.area_id

    area_name = None
    if area_id:
        area = areg.async_get_area(area_id)
        area_name = area.name if area else None

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
                        "message": f"Non-entity member: {m!r}",
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
                    {"code": "CHILD_BUILD_FAILED", "message": str(ex), "entity_id": m}
                )

        if not base.get("device_id") and group_entities:
            base["device_id"] = group_entities[0].get("device_id")
            base["device_name"] = group_entities[0].get("device_name")
        if not base.get("area_id") and group_entities:
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
        f"entity_info: entities={ents!r} flatten_members={flat!r} dedupe={ddp!r} request_id={rid!r}"
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
                    "message": f"Not a valid entity_id: {e!r}",
                    "entity_id": None,
                }
            )
            continue
        try:
            items.append(_build_entry(hass, e, dreg, ereg, areg, errors))
        except Exception as ex:
            errors.append(
                {"code": "ENTRY_BUILD_FAILED", "message": str(ex), "entity_id": e}
            )

    if flat:
        try:
            flat_items = list(items)
            seen = set(
                i.get("entity_id")
                for i in flat_items
                if isinstance(i.get("entity_id"), str)
            )

            for entry in items:
                for child in entry.get("group_entities", []) or []:
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

    try:
        items_json = json.dumps(items)
    except Exception as ex:
        errors.append(
            {"code": "JSON_DUMPS_FAILED", "message": str(ex), "entity_id": None}
        )
        items_json = json.dumps(
            [{"entity_id": i.get("entity_id"), "error": "json_failed"} for i in items]
        )

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
    log.info(f"entity_info: returned {len(items)} items; errors={len(errors)}")
