# Actions
> Steps an automation or script runs: service calls, delays, waits, choose, if/then, repeat, variables, notifications.

```yaml
actions:
  # Call a service. Entities go in target; settings go in data.
  - action: light.turn_on
    target:
      entity_id: [light.kitchen, light.hall]
    data:
      brightness_pct: 60
      transition: 2
  - delay: "00:05:00"
  # Wait until something is true (with a timeout)
  - wait_template: "{{ is_state('binary_sensor.door', 'off') }}"
    timeout: "00:10:00"
    continue_on_timeout: true
  - wait_for_trigger:
      - trigger: state
        entity_id: binary_sensor.motion
        to: "off"
        for: "00:03:00"
  # Branches
  - if:
      - condition: state
        entity_id: sun.sun
        state: below_horizon
    then:
      - action: light.turn_on
        target: {entity_id: light.porch}
    else:
      - action: light.turn_off
        target: {entity_id: light.porch}
  - choose:
      - conditions: [{condition: trigger, id: arrive}]
        sequence: [{action: scene.turn_on, target: {entity_id: scene.welcome}}]
    default: []
  # Loops
  - repeat:
      count: 3
      sequence:
        - action: light.toggle
          target: {entity_id: light.hall}
        - delay: 1
  # Variables and templates
  - variables:
      level: "{{ states('sensor.battery') | int(0) }}"
  - action: notify.mobile_app_pixel
    data:
      title: Battery
      message: "Battery is at {{ level }}%"
  # Run another script, scene or automation
  - action: script.bedtime
  - action: scene.turn_on
    target: {entity_id: scene.movie}
  - stop: "Nothing to do"
```

Notes:
- Use `list_services` with a domain to see a service's exact fields before calling it.
- The entity's domain decides the service: `input_boolean.x` uses
  `input_boolean.turn_on`, `switch.x` uses `switch.turn_on`. `homeassistant.turn_on`
  works for any on/off entity.
- Notification services are named per device (`notify.mobile_app_<device>`). Look them
  up with `list_services` domain `notify`.
