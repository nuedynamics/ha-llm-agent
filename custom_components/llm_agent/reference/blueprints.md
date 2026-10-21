# Blueprints
> Reusable automation and script templates: write one under blueprints/, then use it from an automation.

A blueprint is a YAML file at `blueprints/automation/<folder>/<name>.yaml` (or
`blueprints/script/...`). Write it with `write_file`; it is checked against HA's blueprint
schema before saving. Inputs are referenced with `!input`:

```yaml
blueprint:
  name: Motion light
  description: Turn a light on when motion is seen and off after a delay.
  domain: automation
  input:
    motion:
      name: Motion sensor
      selector:
        entity:
          filter:
            - domain: binary_sensor
              device_class: motion
    light:
      name: Light
      selector:
        target:
          entity:
            - domain: light
    wait:
      name: Off after
      default: 120
      selector:
        number:
          min: 10
          max: 3600
          unit_of_measurement: seconds
mode: restart
triggers:
  - trigger: state
    entity_id: !input motion
    to: "on"
actions:
  - action: light.turn_on
    target: !input light
  - wait_for_trigger:
      - trigger: state
        entity_id: !input motion
        to: "off"
  - delay:
      seconds: !input wait
  - action: light.turn_off
    target: !input light
```

Use it: save an automation with `save_config_item` (kind `automation`) whose config is
only the name and `use_blueprint`. The path is relative to `blueprints/automation/`:

```json
{"alias": "Hallway motion light", "use_blueprint": {"path": "llm_agent/motion_light.yaml", "input": {"motion": "binary_sensor.hallway_motion", "light": {"entity_id": "light.hallway"}, "wait": 180}}}
```

List blueprints with `ha_websocket` `blueprint/list` `{"domain": "automation"}`.
To turn an existing automation into a blueprint, read it, replace the entity ids the
user wants to vary with `!input` names, and add the `blueprint:` header. Use the folder
`llm_agent` for blueprints you write.
