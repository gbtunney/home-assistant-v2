# Notify wrappers that present existing scripts as notify actions.
#
# Save as config/pyscript/alexa_notify.py. Pyscript loads it automatically and
# reloads it on every save. The wrapped scripts are not changed.
#
# Services registered:
#   notify.alexa_sound runs script.custom_alexa_notification_ui
#   notify.func_dispatch_notification runs script.notification_dispatcher
#
# Both take the standard legacy notify arguments message, title, data and
# target, so they work anywhere a legacy notify action works, including Alert
# Redux notifier groups, notify groups and automations.
#
# Keys in data that the wrappers use themselves and never pass to a script:
#   priority   Alexa only. Alert Redux priority. Picks the sound and volume
#              from PRIORITY_SOUNDS and LOUD_PRIORITIES when data sets none.
#   reason     Why the notification is being sent, on, reminder or done.
#   skip       Reasons to drop silently, for example done.
#   entities   Alexa only. Entity ids to describe with the semantic script.
#   semantic   Alexa only. Set to false to speak the message as is.
#   condition  Alexa only. Problem condition for the semantic script.
#              Defaults to the message. An empty value gives a plain status
#              report with no alert wording.
# Every other key in data is passed to the script as one of its fields.
#
# Quiet hours, muting and repeats are handled by Alert Redux. Volume stays with
# the Alexa script, which raises the speaker for the announcement and restores
# it afterwards.
#
# Example Alert Redux notifier group member, action notify.alexa_sound, data:
#
#   priority: "{{ priority }}"
#   reason: "{{ reason }}"
#   skip: [done]
#   entities: "{{ subject_entity_id }}"

ALEXA_SCRIPT = "custom_alexa_notification_ui"
DISPATCH_SCRIPT = "notification_dispatcher"
SEMANTIC_SCRIPT = "gbt_generic_semantic"

# Defaults the Notification Dispatcher sends today, used only when data omits them.
DEFAULT_SPEAKER = "media_player.alexa_s_baby"
DEFAULT_VOLUME = "Normal Volume"
LOUD_VOLUME = "Maximum Volume"

# Sound for each Alert Redux priority, used when data sets no sound. Edit freely.
PRIORITY_SOUNDS = {
    "emergency": "air_horn_03",
    "critical": "amzn_sfx_scifi_alarm_04",
    "warning": "amzn_sfx_scifi_alarm_01",
    "notice": "amzn_sfx_doorbell_chime_01",
    "informational": "bell_02",
}

# Priorities announced at LOUD_VOLUME when data sets no volume.
LOUD_PRIORITIES = ("emergency", "critical")

# Alert Redux sends this message to clear a phone notification. There is nothing to say.
CLEAR_MESSAGE = "clear_notification"

# Keys in data that the wrappers consume. Everything else goes to the script.
OWN_KEYS = ("priority", "reason", "skip", "entities", "semantic", "condition")


def _as_list(value):
    """Normalise a value that may be a list or a comma separated string.

    Args:
        value: None, a comma separated string, or any iterable.

    Returns:
        A list of stripped, non empty strings, or the items of the iterable.
    """
    if not value:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return list(value)


def _is_off(value):
    """Tell whether a flag in data was explicitly turned off.

    Args:
        value: The flag as it arrived, a bool or a string from a template.

    Returns:
        True when the flag is False, 0, false, off or no.
    """
    return value in (False, 0, "false", "False", "off", "Off", "no", "No")


def _skipped(message, data):
    """Decide whether a notification should be dropped without sending.

    Args:
        message: The notification text.
        data: The data dict of the notification.

    Returns:
        True when the message is the Alert Redux clear call, or when the
        reason in data is one of the reasons listed in skip.
    """
    if message == CLEAR_MESSAGE:
        return True
    reason = data.get("reason")
    return bool(reason) and reason in _as_list(data.get("skip"))


def _script_fields(data):
    """Copy the keys in data that belong to the target script.

    Args:
        data: The data dict of the notification.

    Returns:
        A new dict without the keys listed in OWN_KEYS.
    """
    return {key: value for key, value in data.items() if key not in OWN_KEYS}


def _apply_priority(fields, priority):
    """Fill sound and volume from the Alert Redux priority.

    Values already in fields are kept, so data can always override the
    priority. An unknown or missing priority leaves the sound unset and uses
    DEFAULT_VOLUME.

    Args:
        fields: The script fields being built, changed in place.
        priority: The Alert Redux priority, such as critical or notice.
    """
    priority = str(priority or "").strip().lower()
    if priority in PRIORITY_SOUNDS:
        fields.setdefault("sound", PRIORITY_SOUNDS[priority])
    fields.setdefault("volume", LOUD_VOLUME if priority in LOUD_PRIORITIES else DEFAULT_VOLUME)


def _semantic_text(entities, condition, fallback):
    """Turn entities and a condition into a spoken report.

    Calls the semantic script and returns the text in its response. Any
    failure is logged and the fallback is used, so a broken AI step never
    stops the sound from playing.

    Args:
        entities: Entity ids to describe.
        condition: Problem condition text, or empty for a neutral report.
        fallback: Text to return when the semantic script fails or is empty.

    Returns:
        The report text, or the fallback.
    """
    try:
        response = service.call(
            "script",
            SEMANTIC_SCRIPT,
            blocking=True,
            return_response=True,
            input_entities=entities,
            condition=condition,
        )
    except Exception as err:
        log.warning(f"notify.alexa_sound: script.{SEMANTIC_SCRIPT} failed ({err}); using the plain message")
        return fallback
    text = (response or {}).get("text")
    return text if text else fallback


def _run_script(notifier, script_id, fields):
    """Run a script with the given fields and log what was sent.

    Args:
        notifier: The notify service name, used in log messages.
        script_id: The object id of the script, without the script domain.
        fields: The field values for the script.
    """
    if not service.has_service("script", script_id):
        log.error(f"{notifier}: script.{script_id} doesn't exist, nothing sent")
        return
    log.info(f"{notifier} -> script.{script_id} {fields}")
    service.call("script", script_id, blocking=True, **fields)


@service("notify.alexa_sound")
def alexa_sound(message=None, title=None, data=None, target=None, **kwargs):
    """yaml
name: Alexa sound
description: |
  Speak a notification on Alexa with the Alexa Custom Notification UI script, optionally rewritten into a spoken report first.

  | Data key | What it does | Example |
  |---|---|---|
  | priority | Alert Redux priority, picks the sound and volume | {{ priority }} |
  | sound | Sound played before and after the message, overrides priority | amzn_sfx_doorbell_chime_01 |
  | volume | Maximum Volume, Normal Volume or Current, overrides priority | Normal Volume |
  | target_alexa_speaker | Speaker to use, defaults to Alexa baby | entity_id media_player.alexa_s_baby |
  | reason | Why it was sent, on, reminder or done | {{ reason }} |
  | skip | Reasons to stay silent | done |
  | entities | Entities to describe with the semantic script | sensor.cat_fountain_water_volume |
  | semantic | Set false to speak the message as is | false |
  | condition | Problem for the semantic script, empty gives a status report | water is low |
fields:
  message:
    name: Message
    description: Text to speak, or the problem condition when data has entities.
    required: true
    example: Cat fountain water is below its limit
    selector:
      text:
  title:
    name: Title
    description: Ignored because Alexa speaks the message only. Alert Redux sends the alert name here.
    selector:
      text:
  data:
    name: Data
    description: Script fields sound, volume and target_alexa_speaker, plus the wrapper keys priority, reason, skip, entities, semantic and condition.
    default:
      priority: notice
    example:
      priority: warning
      skip:
        - done
      entities: sensor.cat_fountain_water_volume
    selector:
      object:
  target:
    name: Target
    description: Alexa media player to speak on when data has no target_alexa_speaker.
    example: media_player.alexa_s_baby
    selector:
      entity:
        filter:
          domain: media_player
"""
    data = dict(data or {})
    if _skipped(message, data):
        return

    entities = _as_list(data.get("entities"))
    if entities and data.get("reason") != "done" and not _is_off(data.get("semantic", True)):
        condition = data.get("condition", message)
        message = _semantic_text(entities, condition or "", message)

    fields = _script_fields(data)
    fields["message"] = message
    fields.setdefault("title", "")
    _apply_priority(fields, data.get("priority"))
    if "target_alexa_speaker" not in fields:
        speaker = _as_list(target) or [DEFAULT_SPEAKER]
        fields["target_alexa_speaker"] = {"entity_id": speaker[0] if len(speaker) == 1 else speaker}

    _run_script("notify.alexa_sound", ALEXA_SCRIPT, fields)


@service("notify.func_dispatch_notification")
def func_dispatch_notification(message=None, title=None, data=None, target=None, **kwargs):
    """yaml
name: Dispatch notification
description: Run the Notification Dispatcher script as a notifier, passing everything in data except reason and skip as its fields.
fields:
  message:
    name: Message
    description: Notification text, passed to the script as message.
    required: true
    example: CO2 is on
    selector:
      text:
  title:
    name: Title
    description: Optional title, passed to the script as title.
    selector:
      text:
  data:
    name: Data
    description: The fields of the dispatcher such as notification_channel and alexa_sound, plus the wrapper keys reason and skip.
    example:
      notification_channel:
        - alexa
      alexa_sound: amzn_sfx_trumpet_bugle_04
    selector:
      object:
  target:
    name: Target
    description: Optional target, passed to the script as target.
    selector:
      object:
"""
    data = dict(data or {})
    if _skipped(message, data):
        return

    fields = _script_fields(data)
    fields["message"] = message
    if title:
        fields.setdefault("title", title)
    if target:
        fields.setdefault("target", target)

    _run_script("notify.func_dispatch_notification", DISPATCH_SCRIPT, fields)
