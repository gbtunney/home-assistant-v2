@service
def hello_world(action=None, id=None):
    """yaml
    name: Service example
    description: hello_world service example using pyscript.
    fields:
      action:
         description: turn_on turns on the light, fire fires an event
         example: turn_on
         required: true
         selector:
           select:
             options:
               - turn_on
               - fire
      id:
         description: id of light, or name of event to fire
         example: kitchen.light
         required: true
         selector:
           text:
    """
    log.info(f"hello world: got action {action}")
    if action == "turn_on" and id is not None:
        light.turn_on(entity_id=id, brightness=255)
    elif action == "fire" and id is not None:
        event.fire(id)
