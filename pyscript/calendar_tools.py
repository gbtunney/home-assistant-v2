import datetime
import hashlib

"""
Calendar & Date Formatting Tools
"""


@pyscript_compile
def get_suffix(day):
    if 11 <= day <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


@pyscript_compile
def infer_calendar_source(entity_id):
    eid = str(entity_id or "").lower()

    if "google" in eid:
        return "google"
    if "icloud" in eid:
        return "icloud"
    if "caldav" in eid:
        return "caldav"
    if "local" in eid:
        return "local"

    return "unknown"


@pyscript_compile
def make_event_id(event, entity_id=None):
    key = (
        f"{entity_id or ''}|"
        f"{event.get('start', '')}|"
        f"{event.get('end', '')}|"
        f"{event.get('summary', '')}|"
        f"{event.get('location', '')}"
    )
    return hashlib.md5(key.encode("utf-8")).hexdigest()


@pyscript_compile
def parse_datetime_value(value, fallback=None):
    if not value:
        dt = fallback or datetime.datetime.now()
    elif isinstance(value, datetime.datetime):
        dt = value
    else:
        raw = str(value).strip()

        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"

        if "T" not in raw and " " not in raw:
            raw = raw + "T00:00:00"

        dt = datetime.datetime.fromisoformat(raw)

    return dt


@pyscript_compile
def to_local_datetime(value, fallback=None):
    dt = parse_datetime_value(value, fallback=fallback)

    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)

    return dt


@pyscript_compile
def normalize_date_time(value, fallback=None):
    dt = to_local_datetime(value, fallback=fallback)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


@pyscript_compile
def safe_iso_local(value):
    try:
        dt = to_local_datetime(value)
        return dt.isoformat()
    except Exception:
        return str(value or "")


@pyscript_compile
def normalize_event(event, entity_id=None, origin=None):
    start_raw = event.get("start")
    end_raw = event.get("end")

    start_str = str(start_raw or "")
    end_str = str(end_raw or "")

    all_day = "T" not in start_str
    now = datetime.datetime.now()

    try:
        start_dt = to_local_datetime(start_raw)
        end_dt = to_local_datetime(end_raw)
        today = datetime.date.today()

        is_today = start_dt.date() == today
        is_past = end_dt < now
        is_future = start_dt > now
        is_multi_day = end_dt.date() != start_dt.date()
        duration_min = int((end_dt - start_dt).total_seconds() / 60)
    except Exception:
        is_today = False
        is_past = False
        is_future = False
        is_multi_day = False
        duration_min = None

    return {
        "id": make_event_id(event, entity_id=entity_id),
        "title": str(event.get("summary", "")).strip(),
        "description": event.get("description"),
        "location": event.get("location"),
        "start": start_str,
        "end": end_str,
        "start_local": safe_iso_local(start_raw),
        "end_local": safe_iso_local(end_raw),
        "all_day": all_day,
        "duration_min": duration_min,
        "is_today": is_today,
        "is_past": is_past,
        "is_future": is_future,
        "is_multi_day": is_multi_day,
        "transport": "home_assistant",
        "calendar_source": infer_calendar_source(entity_id),
        "origin": origin or "unknown",
        "entity_id": entity_id,
        "raw": event,
    }


@service(supports_response="only")
def get_events_range(
    entity_id=None,
    start_time=None,
    end_time=None,
    summary_filter=None,
    origin=None,
):
    """yaml
    name: Get Events Range
    description: Fetches events for a calendar within a range, with an optional keyword filter.

    fields:
      entity_id:
        name: Calendar Entity
        description: The calendar to fetch events from.
        example: calendar.target_work
        required: true
        selector:
          entity:
            filter:
              domain: calendar

      start_time:
        name: Start Time
        description: Beginning of range. Defaults to now.
        selector:
          datetime:

      end_time:
        name: End Time
        description: End of range. Defaults to 7 days from now.
        selector:
          datetime:

      summary_filter:
        name: Keyword Filter
        description: Only return events containing this word.
        example: "Work"
        selector:
          text:

      origin:
        name: Origin
        description: Optional provenance label such as facebook, manual, imported_ics, or unknown.
        example: "facebook"
        selector:
          text:

    response:
      events:
        description: Matching normalized calendar events
      count:
        description: Number of matching events
    """
    if not entity_id:
        return {"events": [], "count": 0}

    now = datetime.datetime.now()

    start_time = normalize_date_time(start_time, fallback=now)
    end_time = normalize_date_time(
        end_time,
        fallback=now + datetime.timedelta(days=7),
    )

    result = calendar.get_events(
        entity_id=entity_id,
        start_date_time=start_time,
        end_date_time=end_time,
        return_response=True,
    )

    raw_events = result.get(entity_id, {}).get("events", [])

    if summary_filter and str(summary_filter).strip():
        needle = str(summary_filter).strip().lower()
        filtered_events = [
            event
            for event in raw_events
            if needle in str(event.get("summary", "")).lower()
        ]
    else:
        filtered_events = raw_events

    normalized_events = [
        normalize_event(event, entity_id=entity_id, origin=origin)
        for event in filtered_events
    ]

    return {
        "events": normalized_events,
        "count": len(normalized_events),
    }


@service(supports_response="only")
def format_natural_date(date_and_time=None):
    """yaml
    name: Format DateTime to natural language
    description: Converts a timestamp into a friendly, natural language sentence.

    fields:
      date_and_time:
        name: DateTime
        description: The timestamp to format. Supports ISO, timezone offsets, and date-only values.
        example: "2026-03-20T10:00:00.000Z"
        selector:
          datetime:
        required: true

    response:
      natural_date:
        name: Natural Date
        description: Human-readable formatted date time string.
        example: "Tomorrow, friday the 20th at 10:00am"
    """
    try:
        dt = parse_datetime_value(
            date_and_time,
            fallback=datetime.datetime.now(),
        )

        if dt.tzinfo is not None:
            dt = dt.astimezone()

        today = datetime.date.today()
        target_date = dt.date()
        diff = (target_date - today).days

        day_name = dt.strftime("%A").lower()
        month_name = dt.strftime("%B").lower()
        time_str = dt.strftime("%-I:%M%p").lower()
        suffix = get_suffix(dt.day)

        year_str = f" {dt.year}" if dt.year != today.year else ""

        if diff == 0:
            phrase = f"today, {day_name} the {dt.day}{suffix}{year_str} at {time_str}"
        elif diff == 1:
            phrase = (
                f"tomorrow, {day_name} the {dt.day}{suffix}{year_str} at {time_str}"
            )
        elif 1 < diff <= 7:
            phrase = f"{day_name} the {dt.day}{suffix}{year_str} at {time_str}"
        else:
            phrase = f"{month_name} {dt.day}{suffix}{year_str} at {time_str}"

        final_phrase = phrase[0].upper() + phrase[1:]
        return {"natural_date": final_phrase}

    except Exception as e:
        return {"natural_date": f"Error parsing: {str(e)}"}
