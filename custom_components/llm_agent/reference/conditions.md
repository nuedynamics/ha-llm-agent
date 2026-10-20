# Conditions
> Checks that must pass: state, numeric_state, time and weekdays, sun, zone, template, trigger, and/or/not.

```yaml
conditions:
  - condition: state
    entity_id: alarm_control_panel.home
    state: armed_away
  - condition: numeric_state
    entity_id: sensor.living_room_lux
    below: 50
  # Time window and weekdays (mon tue wed thu fri sat sun)
  - condition: time
    after: "22:00:00"
    before: "06:00:00"
    weekday: [mon, tue, wed, thu, fri]
  - condition: sun
    after: sunset
  - condition: zone
    entity_id: person.alex
    zone: zone.home
  - condition: template
    value_template: "{{ is_state('input_boolean.guest_mode', 'off') }}"
  # Which trigger fired (needs `id` on the trigger)
  - condition: trigger
    id: night
  # Combine
  - condition: or
    conditions:
      - condition: state
        entity_id: person.alex
        state: home
      - condition: state
        entity_id: person.sam
        state: home
  - condition: not
    conditions:
      - condition: state
        entity_id: input_boolean.vacation
        state: "on"
```

Notes:
- All conditions in the list must pass (an implicit `and`).
- A `time` window may cross midnight (`after: "22:00:00"`, `before: "06:00:00"`).
- Shorthand inside actions: `- condition: state` works as a step that stops the sequence
  when it fails.
