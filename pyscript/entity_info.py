# /config/pyscript/entity_info.py
import json
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import area_registry as ar

BINARY_DOMAINS = {"light", "switch", "binary_sensor", "input_boolean"}

log.info("Loaded entity_info.py")  # helps confirm file is loading


def _norm_state(hass, entity_id: str, domain: str):
    st = hass.states.get(entity_id)
    raw = st.state if st else "unknown"
    if domain in BINARY_DOMAINS:
        normalized = (
            raw if raw in ("on", "off", "unavailable", "unknown") else "unknown"
        )
        kind = "binary"
        num = None
    else:
        try:
            num = float(raw)
            kind = "number"
        except (ValueError, TypeError):
            num = None
            kind = "text"
        normalized = raw
    return normalized, kind, num


def _labels_from_device(device):
    try:
        lbl = getattr(device, "labels", []) or []
        return list(lbl) if hasattr(lbl, "__iter__") else []
    except Exception:
        return []


def _core_entity(hass, entity_id: str, dreg, ereg, areg):
    entry = ereg.async_get(entity_id)
    dev_id = entry.device_id if entry else None
    device = dreg.async_get(dev_id) if dev_id else None

    domain = entity_id.split(".")[0]
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


def _build_entry(hass, entity_id: str, dreg, ereg, areg):
    base = _core_entity(hass, entity_id, dreg, ereg, areg)
    group_members = []
    st = hass.states.get(entity_id)
    if st:
        members = st.attributes.get("entity_id", [])
        if isinstance(members, (list, tuple)):
            group_members = list(members)

    is_group = len(group_members) > 0
    base["group"] = is_group

    group_entities = []
    if is_group:
        for m in group_members:
            group_entities.append(_core_entity(hass, m, dreg, ereg, areg))

        if not base.get("device_id") and group_entities:
            base["device_id"] = group_entities[0].get("device_id")
            base["device_name"] = group_entities[0].get("device_name")
        if not base.get("area_id") and group_entities:
            base["area_id"] = group_entities[0].get("area_id")
            base["area_name"] = group_entities[0].get("area_name")

    base["group_entities"] = group_entities
    return base


@service
def entity_info(entities=None, flatten_members=False, dedupe=True):
    """Emit entity info for one or many entities via event 'entity_info_list_return'."""
    # Coerce inputs defensively (PyScript/HA sometimes passes strings)
    if entities is None:
        entities = []
    if isinstance(entities, str):
        entities = [entities]

    if isinstance(flatten_members, str):
        flatten_members = flatten_members.strip().lower() in ("1", "true", "yes", "on")
    else:
        flatten_members = bool(flatten_members)

    if isinstance(dedupe, str):
        dedupe = dedupe.strip().lower() in ("1", "true", "yes", "on")
    else:
        dedupe = bool(dedupe)

    log.info(
        f"entity_info: entities={entities!r} flatten_members={flatten_members!r} dedupe={dedupe!r}"
    )

    dreg = dr.async_get(hass)
    ereg = er.async_get(hass)
    areg = ar.async_get(hass)

    # Build entries safely (never let one bad entity kill the whole service)
    items = []
    for e in entities:
        try:
            items.append(_build_entry(hass, e, dreg, ereg, areg))
        except Exception as ex:
            log.exception(f"entity_info: failed building entry for {e!r}: {ex}")

    # Flatten safely
    if flatten_members:
        try:
            flat = list(items)
            seen = set()
            for e in flat:
                eid = e.get("entity_id")
                if isinstance(eid, str):
                    seen.add(eid)

            for entry in items:
                for child in entry.get("group_entities", []) or []:
                    eid = child.get("entity_id")
                    if not isinstance(eid, str):
                        continue
                    if (not dedupe) or (eid not in seen):
                        flat.append(child)
                        seen.add(eid)

            items = flat
        except Exception as ex:
            log.exception(f"entity_info: flatten_members failed: {ex}")

    # JSON encoding can fail if anything weird slips in; guard it.
    try:
        items_json = json.dumps(items)
    except Exception as ex:
        log.exception(f"entity_info: json.dumps failed: {ex}")
        # fall back to a safer string so the event still fires
        items_json = json.dumps(
            [{"entity_id": i.get("entity_id"), "error": "json_failed"} for i in items]
        )

    event.fire("entity_info_list_return", items=items, items_json=items_json)
    log.info(f"entity_info: returned {len(items)} items")
