# Helpers
> Helper entities (input_boolean, input_number, input_select, input_datetime, input_text, counter, timer, template sensors) and how to use them.

Create a simple helper with `ha_websocket`, the same command the HA helper screen uses:

```json
{"command": "input_boolean/create", "payload": {"name": "Guest mode", "icon": "mdi:account"}}
{"command": "input_number/create", "payload": {"name": "Target temp", "min": 15, "max": 25, "step": 0.5}}
{"command": "input_select/create", "payload": {"name": "House mode", "options": ["Home", "Away", "Night"]}}
{"command": "timer/create", "payload": {"name": "Laundry", "duration": "01:00:00"}}
```

The same pattern works for `input_text`, `input_datetime` (`has_date`, `has_time`) and
`counter`. List them with `<domain>/list`. Template helpers are created through the
`template` config flow with the integrations tool.

Using them:
| Helper | Read | Change |
| --- | --- | --- |
| `input_boolean.x` | state `on`/`off` | `input_boolean.turn_on` / `turn_off` / `toggle` |
| `input_number.x` | state is a number string | `input_number.set_value` `{value: 21}` |
| `input_select.x` | state is the option | `input_select.select_option` `{option: "Away"}` |
| `input_datetime.x` | state `HH:MM:SS` or a date | `input_datetime.set_datetime` `{time: "07:30:00"}` |
| `input_text.x` | state is the text | `input_text.set_value` `{value: "hi"}` |
| `counter.x` | number | `counter.increment` / `decrement` / `reset` |
| `timer.x` | `idle`/`active`/`paused` | `timer.start` `{duration: "00:10:00"}`, `timer.cancel` |

Timers fire the event `timer.finished` with `entity_id` in the event data, which an
automation can use as an event trigger.

Template sensor (YAML in configuration.yaml, then check config and reload templates):

```yaml
template:
  - sensor:
      - name: Total power
        unit_of_measurement: W
        state: "{{ states('sensor.a_power') | float(0) + states('sensor.b_power') | float(0) }}"
```
