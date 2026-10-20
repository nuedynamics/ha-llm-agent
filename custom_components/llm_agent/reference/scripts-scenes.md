# Scripts and scenes
> Scripts (reusable action sequences with fields) and scenes (saved entity states).

**Script** (`save_config_item`, kind `script`, with a slug `id` such as `bedtime`):

```yaml
alias: Bedtime
description: Lights off, doors locked, alarm armed.
mode: single
fields:
  delay_minutes:
    description: Minutes before the lights go off
    default: 0
    selector: {number: {min: 0, max: 30}}
sequence:
  - delay: {minutes: "{{ delay_minutes }}"}
  - action: light.turn_off
    target: {area_id: bedroom}
  - action: lock.lock
    target: {entity_id: lock.front_door}
```

Run it with `script.bedtime` (or `script.turn_on`). Scripts use `sequence`, not `actions`.

**Scene** (kind `scene`): the states to restore, per entity.

```yaml
name: Movie
entities:
  light.living_room:
    state: "on"
    brightness: 60
    color_temp_kelvin: 2700
  media_player.tv:
    state: "on"
```

Activate it with `scene.turn_on` and target `scene.movie`. Scenes use `name`, not `alias`.
