# Triggers
> Every trigger type with an example: state, numeric_state, time, time_pattern, sun, event, zone, template, homeassistant.

```yaml
triggers:
  # An entity changes state (optionally from/to, and for how long)
  - trigger: state
    entity_id: binary_sensor.back_door
    to: "on"
    for: "00:02:00"
  # Any attribute or state change: omit to/from. Attribute changes:
  - trigger: state
    entity_id: climate.living_room
    attribute: current_temperature
  # A number crosses a threshold
  - trigger: numeric_state
    entity_id: sensor.outdoor_temperature
    below: 5
  # A time of day (or an input_datetime / timestamp sensor)
  - trigger: time
    at: "07:30:00"
  - trigger: time
    at: input_datetime.wake_up
  # Repeating: every 5 minutes
  - trigger: time_pattern
    minutes: "/5"
  # Sunrise or sunset, with an optional offset
  - trigger: sun
    event: sunset
    offset: "-00:30:00"
  # Someone enters or leaves a zone
  - trigger: zone
    entity_id: person.alex
    zone: zone.home
    event: leave
  # A template turns true
  - trigger: template
    value_template: "{{ states('sensor.power') | float(0) > 3000 }}"
  # An event on the bus (button presses, mobile app actions)
  - trigger: event
    event_type: mobile_app_notification_action
    event_data:
      action: OPEN_GARAGE
  # Home Assistant starts
  - trigger: homeassistant
    event: start
```

Notes:
- State values are strings: `to: "on"`, not `to: on` or `to: true`.
- `for` accepts "HH:MM:SS" or `{minutes: 5}`.
- Give triggers an `id` when actions need to know which one fired
  (`condition: trigger`, or `{{ trigger.id }}`).
- There is no weekday option on triggers. Add a `condition: time` with `weekday`.
