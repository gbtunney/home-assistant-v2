import json
import time

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr


SCHEMA_ID = "snailicide.entity_info.v3"
SCHEMA_VERSION = 3

BINARY_DOMAINS = {"light", "switch", "binary_sensor", "input_boolean"}


log.info("Loaded entity_info.py (v3 response data with semantic metadata)")


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
        return [s] if s else []
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
    return [value for value in _as_str_list(x) if _is_entity_id(value)]


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
        return s if s else _make_request_id()
    except Exception:
        return _make_request_id()


def _parse_args(
    entities,
    areas,
    devices,
    labels,
    flatten_members,
    dedupe,
    request_id,
):
    return (
        _as_entities(entities),
        _as_str_list(areas),
        _as_str_list(devices),
        _as_str_list(labels),
        _as_bool(flatten_members, False),
        _as_bool(dedupe, True),
        _as_request_id(request_id),
    )


def _is_entity_id(x):
    if not isinstance(x, str) or "." not in x:
        return False
    parts = x.split(".", 1)
    return bool(parts[0]) and bool(parts[1])


def _add_unique_str(out, seen, value):
    if not isinstance(value, str) or not value or value in seen:
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
            _add_unique_str(
                out,
                seen,
                getattr(entry, "entity_id", None),
            )

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
            _add_unique_str(
                out,
                seen,
                getattr(entry, "entity_id", None),
            )

        try:
            device_entries = dr.async_entries_for_area(dreg, area_id)
        except Exception:
            device_entries = []

        for device in device_entries:
            device_id = getattr(device, "id", None)

            if not isinstance(device_id, str):
                continue

            try:
                child_entries = er.async_entries_for_device(
                    ereg,
                    device_id,
                )
            except Exception:
                child_entries = []

            for entry in child_entries:
                _add_unique_str(
                    out,
                    seen,
                    getattr(entry, "entity_id", None),
                )

    return out


def _collect_entity_ids_from_labels(
    label_ids,
    areg,
    dreg,
    ereg,
):
    out = []
    seen = set()

    for label_id in label_ids:
        try:
            entity_entries = er.async_entries_for_label(
                ereg,
                label_id,
            )
        except Exception:
            entity_entries = []

        for entry in entity_entries:
            _add_unique_str(
                out,
                seen,
                getattr(entry, "entity_id", None),
            )

        try:
            device_entries = dr.async_entries_for_label(
                dreg,
                label_id,
            )
        except Exception:
            device_entries = []

        for device in device_entries:
            device_id = getattr(device, "id", None)

            if not isinstance(device_id, str):
                continue

            try:
                child_entries = er.async_entries_for_device(
                    ereg,
                    device_id,
                )
            except Exception:
                child_entries = []

            for entry in child_entries:
                _add_unique_str(
                    out,
                    seen,
                    getattr(entry, "entity_id", None),
                )

        try:
            area_entries = ar.async_entries_for_label(
                areg,
                label_id,
            )
        except Exception:
            area_entries = []

        for area in area_entries:
            area_id = getattr(area, "id", None)

            if isinstance(area_id, str):
                area_entities = _collect_entity_ids_from_areas(
                    [area_id],
                    dreg,
                    ereg,
                )

                for entity_id in area_entities:
                    _add_unique_str(
                        out,
                        seen,
                        entity_id,
                    )

    return out


# -----------------------------
# Semantic extraction
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

        return list(labels)

    except Exception:
        return []


def _iso(value):
    if value is None:
        return None

    try:
        return value.isoformat()
    except Exception:
        return str(value)


def _state_age_seconds(st):
    if st is None:
        return None

    if getattr(st, "last_changed", None) is None:
        return None

    try:
        return max(
            0,
            int(time.time() - st.last_changed.timestamp()),
        )
    except Exception:
        return None


def _json_safe(value):
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]

    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}

    try:
        return value.isoformat()
    except Exception:
        return str(value)


def _pick(attrs, keys):
    out = {}

    for key in keys:
        if key in attrs:
            out[key] = _json_safe(attrs[key])

    return out


def _registry_platform(entry):
    if entry is None:
        return None

    platform = getattr(entry, "platform", None)

    if isinstance(platform, str):
        return platform

    return None


def _semantic_meta(domain, st, entry):
    attrs = dict(st.attributes) if st else {}
    platform = _registry_platform(entry)

    meta = {}

    # -----------------------------
    # Sensors
    # -----------------------------

    if domain == "sensor":
        meta.update(
            _pick(
                attrs,
                (
                    "device_class",
                    "state_class",
                    "unit_of_measurement",
                    "suggested_display_precision",
                    "suggested_unit_of_measurement",
                ),
            )
        )

    # -----------------------------
    # Binary sensors / Threshold
    # -----------------------------

    elif domain == "binary_sensor":
        meta.update(_pick(attrs, ("device_class",)))

        if platform == "threshold":
            meta["helper_type"] = "threshold"

            meta.update(
                _pick(
                    attrs,
                    (
                        "entity_id",
                        "source_entity",
                        "lower",
                        "upper",
                        "hysteresis",
                        "lower_limit",
                        "upper_limit",
                    ),
                )
            )

    # -----------------------------
    # Input Number
    # -----------------------------

    elif domain == "input_number":
        meta["helper_type"] = "input_number"

        meta.update(
            _pick(
                attrs,
                (
                    "min",
                    "max",
                    "step",
                    "mode",
                    "unit_of_measurement",
                ),
            )
        )

    # -----------------------------
    # Input Select
    # -----------------------------

    elif domain == "input_select":
        meta["helper_type"] = "input_select"

        meta.update(_pick(attrs, ("options",)))

    # -----------------------------
    # Input Datetime
    # -----------------------------

    elif domain == "input_datetime":
        meta["helper_type"] = "input_datetime"

        meta.update(
            _pick(
                attrs,
                (
                    "has_date",
                    "has_time",
                    "year",
                    "month",
                    "day",
                    "hour",
                    "minute",
                    "second",
                    "timestamp",
                ),
            )
        )

    # -----------------------------
    # Input Boolean
    # -----------------------------

    elif domain == "input_boolean":
        meta["helper_type"] = "input_boolean"

    # -----------------------------
    # Counter
    # -----------------------------

    elif domain == "counter":
        meta["helper_type"] = "counter"

        meta.update(
            _pick(
                attrs,
                (
                    "initial",
                    "step",
                    "minimum",
                    "maximum",
                ),
            )
        )

    # -----------------------------
    # Timer
    # -----------------------------

    elif domain == "timer":
        meta["helper_type"] = "timer"

        meta.update(
            _pick(
                attrs,
                (
                    "duration",
                    "remaining",
                    "finishes_at",
                    "restore",
                ),
            )
        )

    # -----------------------------
    # Schedule
    # -----------------------------

    elif domain == "schedule":
        meta["helper_type"] = "schedule"

        meta.update(_pick(attrs, ("next_event",)))

    # -----------------------------
    # Number
    # -----------------------------

    elif domain == "number":
        meta.update(
            _pick(
                attrs,
                (
                    "min",
                    "max",
                    "step",
                    "mode",
                    "unit_of_measurement",
                    "device_class",
                ),
            )
        )

    # -----------------------------
    # Select
    # -----------------------------

    elif domain == "select":
        meta.update(_pick(attrs, ("options",)))

    # -----------------------------
    # Climate
    # -----------------------------

    elif domain == "climate":
        meta.update(
            _pick(
                attrs,
                (
                    "hvac_modes",
                    "hvac_action",
                    "preset_modes",
                    "preset_mode",
                    "current_temperature",
                    "temperature",
                    "target_temp_high",
                    "target_temp_low",
                    "min_temp",
                    "max_temp",
                    "target_temp_step",
                    "temperature_unit",
                    "humidity",
                    "current_humidity",
                ),
            )
        )

    # -----------------------------
    # Light
    # -----------------------------

    elif domain == "light":
        meta.update(
            _pick(
                attrs,
                (
                    "brightness",
                    "color_mode",
                    "supported_color_modes",
                    "color_temp_kelvin",
                    "min_color_temp_kelvin",
                    "max_color_temp_kelvin",
                    "rgb_color",
                    "xy_color",
                    "effect",
                    "effect_list",
                ),
            )
        )

    # -----------------------------
    # Switch / Button
    # -----------------------------

    elif domain in ("switch", "button"):
        meta.update(_pick(attrs, ("device_class",)))

    # Preserve integration/helper identity.
    if platform:
        meta["platform"] = platform

    return meta


# -----------------------------
# Core entity record
# -----------------------------


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

    if entry and getattr(entry, "area_id", None):
        area_id = entry.area_id

    elif device and getattr(device, "area_id", None):
        area_id = device.area_id

    area_name = None

    if area_id:
        area = areg.async_get_area(area_id)

        if area:
            area_name = area.name

    device_name = None
    device_default_name = None

    if device:
        device_default_name = device.name or device.model
        device_name = device.name_by_user or device_default_name

    state, state_kind, state_number = _norm_state(
        hass,
        entity_id,
        domain,
    )

    attrs = _json_safe(dict(st.attributes)) if st else {}

    return {
        "entity_id": entity_id,
        "domain": domain,
        "platform": _registry_platform(entry),
        "name": name,
        "state": state,
        "state_kind": state_kind,
        "state_number": state_number,
        "last_changed": (_iso(st.last_changed) if st else None),
        "last_updated": (_iso(st.last_updated) if st else None),
        "state_age_seconds": _state_age_seconds(st),
        "attributes": attrs,
        "semantic": _semantic_meta(
            domain,
            st,
            entry,
        ),
        "device_id": dev_id,
        "device_name": device_name,
        "device_default_name": device_default_name,
        "device_labels": (_labels_from_entry(device) if device else []),
        "entity_labels": (_labels_from_entry(entry) if entry else []),
        "area_id": area_id,
        "area_name": area_name,
    }


# -----------------------------
# Groups
# -----------------------------


def _build_entry(
    hass,
    entity_id,
    dreg,
    ereg,
    areg,
    errors,
):
    base = _core_entity(
        hass,
        entity_id,
        dreg,
        ereg,
        areg,
    )

    group_members = []

    st = hass.states.get(entity_id)

    if st:
        members = st.attributes.get(
            "entity_id",
            [],
        )

        if isinstance(members, (list, tuple)):
            group_members = list(members)

    valid_members = []

    for member in group_members:
        if not _is_entity_id(member):
            if member is not None:
                errors.append(
                    {
                        "code": "BAD_GROUP_MEMBER",
                        "message": "Non-entity member: %r" % (member,),
                        "entity_id": entity_id,
                    }
                )

            continue

        valid_members.append(member)

    is_group = len(valid_members) > 0

    base["group"] = is_group
    base["group_member_count"] = len(valid_members)

    group_entities = []

    if is_group:
        for member in valid_members:
            if hass.states.get(member) is None and ereg.async_get(member) is None:
                errors.append(
                    {
                        "code": "MISSING_MEMBER",
                        "message": "Member not found in state/registry",
                        "entity_id": member,
                    }
                )

                continue

            try:
                group_entities.append(
                    _core_entity(
                        hass,
                        member,
                        dreg,
                        ereg,
                        areg,
                    )
                )

            except Exception as ex:
                errors.append(
                    {
                        "code": "CHILD_BUILD_FAILED",
                        "message": str(ex),
                        "entity_id": member,
                    }
                )

        if not base.get("device_id") and group_entities:
            first = group_entities[0]

            base["device_id"] = first.get("device_id")
            base["device_name"] = first.get("device_name")
            base["device_default_name"] = first.get("device_default_name")
            base["device_labels"] = first.get("device_labels")

        if not base.get("area_id") and group_entities:
            first = group_entities[0]

            base["area_id"] = first.get("area_id")
            base["area_name"] = first.get("area_name")

    base["group_entities"] = group_entities

    return base


# -----------------------------
# Service
# -----------------------------


@service(
    "pyscript.entity_info",
    supports_response="only",
)
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

    description: >
      Fetch semantic metadata for Home Assistant entities,
      areas, devices, or labels, with optional group expansion.

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
        description: >
          One or more areas. Entities from these areas
          will be included.
        selector:
          area:
            multiple: true

      devices:
        name: Devices
        description: >
          One or more devices. Entities from these devices
          will be included.
        selector:
          device:
            multiple: true

      labels:
        name: Labels
        description: >
          Select one or more labels. Matching labeled
          entities, devices, and areas will be expanded
          to entities.
        selector:
          label:
            multiple: true

      flatten_members:
        name: Flatten group members
        description: >
          Include group members as top-level items
          in the returned response.
        default: false
        selector:
          boolean:

      dedupe:
        name: Dedupe flattened members
        description: >
          When flattening, avoid returning duplicate
          entity IDs.
        default: true
        selector:
          boolean:

      request_id:
        name: Request ID
        description: >
          Optional label for this request.
          If omitted, one is generated automatically
          and echoed in the response.
        example: kitchen-check
        selector:
          text:

    response:

      schema_id:
        description: Stable schema identifier

      version:
        description: Schema version

      request_id:
        description: >
          Provided or auto-generated request identifier

      meta:
        description: Summary metadata about the result set

      errors:
        description: Any validation or processing errors

      items:
        description: >
          Structured semantic entity records including
          state timing, raw attributes, and
          domain/helper metadata.

      items_json:
        description: JSON string of items for templating
    """

    (
        ents,
        area_values,
        device_values,
        label_values,
        flat,
        ddp,
        rid,
    ) = _parse_args(
        entities,
        areas,
        devices,
        labels,
        flatten_members,
        dedupe,
        request_id,
    )

    log.info(
        "entity_info: entities=%r areas=%r devices=%r "
        "labels=%r flatten_members=%r dedupe=%r "
        "request_id=%r"
        % (
            ents,
            area_values,
            device_values,
            label_values,
            flat,
            ddp,
            rid,
        )
    )

    dreg = dr.async_get(hass)
    ereg = er.async_get(hass)
    areg = ar.async_get(hass)
    lreg = lr.async_get(hass)

    errors = []
    items = []

    area_ids = _resolve_area_ids(
        area_values,
        areg,
        errors,
    )

    device_ids = _resolve_device_ids(
        device_values,
        dreg,
        errors,
    )

    label_ids = _resolve_label_ids(
        label_values,
        lreg,
        errors,
    )

    candidate_entity_ids = []
    seen_candidate_entity_ids = set()

    for entity_id in ents:
        _add_unique_str(
            candidate_entity_ids,
            seen_candidate_entity_ids,
            entity_id,
        )

    for entity_id in _collect_entity_ids_from_areas(
        area_ids,
        dreg,
        ereg,
    ):
        _add_unique_str(
            candidate_entity_ids,
            seen_candidate_entity_ids,
            entity_id,
        )

    for entity_id in _collect_entity_ids_from_devices(
        device_ids,
        ereg,
    ):
        _add_unique_str(
            candidate_entity_ids,
            seen_candidate_entity_ids,
            entity_id,
        )

    for entity_id in _collect_entity_ids_from_labels(
        label_ids,
        areg,
        dreg,
        ereg,
    ):
        _add_unique_str(
            candidate_entity_ids,
            seen_candidate_entity_ids,
            entity_id,
        )

    for entity_id in candidate_entity_ids:
        if not _is_entity_id(entity_id):
            errors.append(
                {
                    "code": "BAD_ENTITY_ID",
                    "message": ("Not a valid entity_id: %r" % (entity_id,)),
                    "entity_id": None,
                }
            )

            continue

        try:
            items.append(
                _build_entry(
                    hass,
                    entity_id,
                    dreg,
                    ereg,
                    areg,
                    errors,
                )
            )

        except Exception as ex:
            errors.append(
                {
                    "code": "ENTRY_BUILD_FAILED",
                    "message": str(ex),
                    "entity_id": entity_id,
                }
            )

    root_count = len(items)
    root_group_count = 0
    child_count = 0

    for entry in items:
        if not isinstance(entry, dict):
            continue

        if bool(entry.get("group", False)):
            root_group_count += 1

        children = entry.get("group_entities")

        if isinstance(children, list):
            child_count += len(children)

    flattened_added_count = 0
    deduped_skipped_count = 0

    if flat:
        try:
            flat_items = list(items)
            seen = set()

            for item in flat_items:
                if isinstance(item, dict):
                    eid = item.get("entity_id")

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

                    if not ddp or eid not in seen:
                        flat_items.append(child)
                        seen.add(eid)
                        flattened_added_count += 1

                    else:
                        deduped_skipped_count += 1

            items = flat_items

        except Exception as ex:
            errors.append(
                {
                    "code": "FLATTEN_FAILED",
                    "message": str(ex),
                    "entity_id": None,
                }
            )

    try:
        items_json = json.dumps(items)

    except Exception as ex:
        errors.append(
            {
                "code": "JSON_DUMPS_FAILED",
                "message": str(ex),
                "entity_id": None,
            }
        )

        fallback = []

        for item in items:
            if isinstance(item, dict):
                fallback.append(
                    {
                        "entity_id": item.get("entity_id"),
                        "error": "json_failed",
                    }
                )

            else:
                fallback.append(
                    {
                        "entity_id": None,
                        "error": "json_failed",
                    }
                )

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
            "flattened_added_count": (flattened_added_count),
            "returned_count": len(items),
            "dedupe": ddp,
            "deduped_skipped_count": (deduped_skipped_count),
        },
        "errors": errors,
        "items": items,
        "items_json": items_json,
    }
