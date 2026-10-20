# Templates
> Jinja templates: reading states and attributes, numbers, time, filters, and safe defaults.

Templates go in strings: `"{{ ... }}"`. They work in template triggers and conditions, in
`data` of actions, and in template helpers.

```jinja
{{ states('sensor.outdoor_temperature') }}          {# the state, always a string #}
{{ states('sensor.outdoor_temperature') | float(0) }}  {# as a number, 0 if unavailable #}
{{ is_state('light.kitchen', 'on') }}
{{ state_attr('climate.living_room', 'current_temperature') }}
{{ is_state_attr('media_player.tv', 'source', 'HDMI 1') }}
{{ now().hour >= 22 }}
{{ (now() - states.binary_sensor.door.last_changed).total_seconds() > 600 }}
{{ as_timestamp(states('sensor.next_alarm')) - as_timestamp(now()) }}
{{ states.light | selectattr('state', 'eq', 'on') | map(attribute='entity_id') | list }}
{{ area_entities('kitchen') }}
{{ expand('group.downstairs') | map(attribute='name') | join(', ') }}
{{ trigger.to_state.state }}      {# in automations: what fired #}
{{ value | round(1) }}
```

Rules:
- Always give number filters a default: `float(0)`, `int(0)`. Unavailable sensors
  otherwise break the template.
- States are strings: compare with `'on'`, not `true`.
- `states('x')` returns `unknown` for a missing entity; check the id with `search_entities`.
- Test a template with `render_template` before saving it.
