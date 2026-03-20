# CALENDAR NOTES

#TDOO DO THIS PLS - currently broke if end date is earlier than start

```py
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
    }]
```

```py
now = datetime.datetime.now()

start_dt = to_local_datetime(start_time, fallback=now)
end_dt = to_local_datetime(
    end_time,
    fallback=now + datetime.timedelta(days=7),
)

swapped = False

if end_dt < start_dt:
    start_dt, end_dt = end_dt, start_dt
    swapped = True

start_time = start_dt.strftime("%Y-%m-%d %H:%M:%S")
end_time = end_dt.strftime("%Y-%m-%d %H:%M:%S")



#return it like
return {
    "events": normalized_events,
    "count": len(normalized_events),
    "range": {
        "start": start_time,
        "end": end_time,
        "swapped": swapped,
    },
}
```
