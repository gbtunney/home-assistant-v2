#pyscript/entity_info.py
import json
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import area_registry as ar

BINARY_DOMAINS = {"light", "switch", "binary_sensor", "input_boolean"}

def _norm_state(hass, entity_id: str, domain: str):
    st = hass.states.get(entity_id)
    raw = st.state if st else "unknown"
    if domain in BINARY_DOMAINS:
        normalized = raw if raw in ("on", "off", "unavailable", "unknown") else "unknown"
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
            child = _core_entity(hass, m, dreg, ereg, areg)
            group_entities.append(child)

        if not base.get("device_id") and group_entities:
            base["device_id"] = group_entities[0].get("device_id")
            base["device_name"] = group_entities[0].get("device_name")
        if not base.get("area_id") and group_entities:
            base["area_id"] = group_entities[0].get("area_id")
            base["area_name"] = group_entities[0].get("area_name")

    base["group_entities"] = group_entities
    return base

@service("entity_info")
async def entity_info(entities: list = None, flatten_members: bool = False, dedupe: bool = True):
    """Emit entity info for one or many entities via event 'entity_info_list_return'."""
    if not entities:
        entities = []

    dreg = dr.async_get(hass)
    ereg = er.async_get(hass)
    areg = ar.async_get(hass)

    items = [_build_entry(hass, e, dreg, ereg, areg) for e in entities]

    if flatten_members:
        flat = items[:]
        seen = set(e["entity_id"] for e in flat)
        for entry in items:
            for child in entry.get("group_entities", []):
                eid = child["entity_id"]
                if not dedupe or eid not in seen:
                    flat.append(child)
                    seen.add(eid)
        items = flat

    payload = {"items": items, "items_json": json.dumps(items)}
    event.fire("entity_info_list_return", payload)