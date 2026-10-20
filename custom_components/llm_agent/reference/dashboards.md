# Dashboards
> Dashboard config: views, sections, and the common cards (tile, entities, button, gauge, history-graph, markdown, thermostat, grids).

Save with `save_dashboard`. A new dashboard needs a `url_path` with a hyphen (such as
`living-room`) and a `title`. Leaving out `url_path` replaces the main dashboard. The
config is the complete dashboard; read the current one first when editing.

```json
{"views": [
  {"title": "Living room", "path": "living-room", "type": "sections",
   "sections": [
     {"type": "grid", "cards": [
       {"type": "heading", "heading": "Lights"},
       {"type": "tile", "entity": "light.living_room"},
       {"type": "tile", "entity": "light.lamp", "features": [{"type": "light-brightness"}]}
     ]},
     {"type": "grid", "cards": [
       {"type": "thermostat", "entity": "climate.living_room"},
       {"type": "history-graph", "entities": ["sensor.living_room_temperature"],
        "hours_to_show": 24}
     ]}
   ]}
]}
```

Classic views use `cards` instead of `sections`:
`{"title": "Home", "cards": [{"type": "entities", "entities": ["switch.fan"]}]}`.

Common cards:
| Card | Key fields |
| --- | --- |
| `tile` | `entity`, optional `features` |
| `entities` | `entities` (list of ids or `{entity, name}`), `title` |
| `button` | `entity`, `tap_action: {action: toggle}` |
| `glance` | `entities` |
| `gauge` | `entity`, `min`, `max`, `severity` |
| `history-graph` | `entities`, `hours_to_show` |
| `markdown` | `content` (templates allowed) |
| `thermostat` | `entity` (climate) |
| `media-control` | `entity` (media_player) |
| `weather-forecast` | `entity` (weather) |
| `picture-entity` | `entity` (camera) |
| `vertical-stack`, `horizontal-stack`, `grid` | `cards` |
| `conditional` | `conditions: [{entity, state}]`, `card` |

Notes:
- Every dashboard needs a `views` list (or a `strategy`). Every card needs a `type`.
- Use real entity ids from `search_entities`.
