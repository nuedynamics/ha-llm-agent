# Service calls and targets
> How to call a service with call_service: domain, service, target (entity/area/device/label), data.

With the `call_service` tool:

```json
{"domain": "light", "service": "turn_on",
 "target": {"entity_id": ["light.kitchen"]},
 "data": {"brightness_pct": 40, "color_temp_kelvin": 2700}}
```

- `target` picks what to act on: `entity_id`, `area_id`, `device_id`, `floor_id` or
  `label_id`, each a string or a list. Area ids come from the home summary; entity ids
  come from `search_entities`.
- `data` holds settings only (brightness, temperature, message). Don't put the entity
  in `data`.
- `domain` is the entity's domain: `cover.open_cover` for `cover.garage`,
  `climate.set_temperature` for `climate.living_room`.
- Some services return data (`weather.get_forecasts`, `calendar.get_events`): set
  `return_response` to true.
- Unknown services fail. Run `list_services` without a domain to see what exists, or
  with a domain to see the fields.

Common services:
| Goal | Service | Data |
| --- | --- | --- |
| On, off, toggle | `<domain>.turn_on` / `turn_off` / `toggle` | |
| Brightness | `light.turn_on` | `brightness_pct: 0-100` |
| Colour | `light.turn_on` | `rgb_color: [255, 0, 0]` or `color_temp_kelvin` |
| Thermostat | `climate.set_temperature` | `temperature: 21` |
| Cover position | `cover.set_cover_position` | `position: 0-100` |
| Lock | `lock.lock` / `lock.unlock` | |
| Media | `media_player.volume_set` | `volume_level: 0.0-1.0` |
| Set a helper | `input_number.set_value`, `input_select.select_option`, `input_text.set_value` | `value` / `option` |
| Forecast | `weather.get_forecasts` | `type: daily`, return_response |
