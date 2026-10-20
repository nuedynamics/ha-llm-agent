# Automations
> Shape of an automation: alias, triggers, conditions, actions, mode. Read first.

An automation runs its **actions** when a **trigger** fires and all **conditions** pass.
Save it with `save_config_item` (kind `automation`); the config is a JSON object:

```yaml
alias: Porch light at sunset
description: Turns the porch light on at sunset and off at 23:00.
mode: single            # single | restart | queued | parallel
triggers:
  - trigger: sun
    event: sunset
    id: sunset
  - trigger: time
    at: "23:00:00"
    id: night
conditions: []
actions:
  - choose:
      - conditions:
          - condition: trigger
            id: sunset
        sequence:
          - action: light.turn_on
            target:
              entity_id: light.porch
    default:
      - action: light.turn_off
        target:
          entity_id: light.porch
```

Rules:
- Keys are plural: `triggers`, `conditions`, `actions`. Each trigger starts with
  `trigger:`, each condition with `condition:`, each service call with `action:`.
- `alias` is the name. There is no `name` key.
- Omit `id` when creating; the tool assigns one.
- Days of the week belong in a **condition** (`condition: time` with `weekday`), not in a
  trigger. See conditions.
- Find entity ids with `search_entities` first. Never invent them.

Common mistakes:
- `platform: time` or `service: light.turn_on`: old syntax. Use `trigger: time` and
  `action: light.turn_on`.
- `platform:` inside an action: actions never have a platform.
- `device_id: light.kitchen`: a device id is a long hex string, not an entity id. Use
  `entity_id` in `target`.
- Times as numbers (`hour: 23`): use `at: "23:00:00"`.

Related: triggers, conditions, actions, targets, templates.
