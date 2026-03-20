import datetime

"""
Calendar & Date Formatting Tools
"""
import datetime


@pyscript_compile
def get_suffix(day):
    if 11 <= day <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


@service(supports_response="only")
def get_events_range(
    entity_id=None, start_time=None, end_time=None, summary_filter=None
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
         example: "2026-03-19 00:00:00"
         selector:
           datetime: null
         required: false

      end_time:
         name: End Time
         required: false
         description: End of range. Defaults to 7 days from now.
         example: "2026-03-27 23:59:59"
         selector:
           datetime: null
      summary_filter:
         name: Keyword Filter
         description: Only return events containing this word (e.g., 'Work').
         example: "Work"
         selector:
           text:
    """
    # 1. Handle Dynamic Defaults
    now = datetime.datetime.now()
    if not start_time:
        start_time = now.strftime("%Y-%m-%d %H:%M:%S")
    if not end_time:
        end_time = (now + datetime.timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

    # 2. Call the native Home Assistant calendar service
    # We use task.wait to ensure the response is captured in Pyscript
    result = calendar.get_events(
        entity_id=entity_id,
        start_date_time=start_time,
        end_date_time=end_time,
        return_response=True,
    )

    raw_events = result.get(entity_id, {}).get("events", [])

    # 3. Apply Keyword Filter (if provided)
    if summary_filter:
        filtered_events = [
            e
            for e in raw_events
            if summary_filter.lower() in e.get("summary", "").lower()
        ]
    else:
        filtered_events = raw_events

    return {"events": raw_events, "count": len(filtered_events)}


@service(supports_response="only")
def format_natural_date(date_and_time=None):
    """yaml
    name: Format DateTime to natural language
    description: Converts a timestamp into a friendly, natural language sentence.
    response:
      natural_date:
         name: Natural Date (dictionary)
         description: string Human-readable formatted date time string.
         example: "Tomorrow, friday the 20th at 10:00am"
    fields:
      date_and_time:
         name: DateTime
         description: The timestamp to format. Supports ISO and .000Z.
         example: "2026-03-20T10:00:00.000Z"
         selector:
           datetime: null
         required: true

    """
    if not date_and_time:
        # Default to now if empty
        date_and_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Clean the input: Remove 'Z', change 'T' to space, drop milliseconds
        clean_str = str(date_and_time).replace("Z", "").replace("T", " ").split(".")[0]
        dt = datetime.datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")

        today = datetime.date.today()
        target_date = dt.date()
        diff = (target_date - today).days

        day_name = dt.strftime("%A").lower()
        month_name = dt.strftime("%B").lower()
        time_str = dt.strftime("%-I:%M%p").lower()
        suffix = get_suffix(dt.day)

        # Only add year if it's not the current year
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

        # Sentence-style capitalization
        final_phrase = phrase[0].upper() + phrase[1:]

        return {"natural_date": final_phrase}

    except Exception as e:
        return {"natural_date": f"Error parsing: {str(e)}"}
