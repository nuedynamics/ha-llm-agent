# Packages and python_scripts
> YAML packages (one file bundling config for a feature) and small python_scripts; both need a line in configuration.yaml.

Packages keep everything for one feature in one file under `packages/`. They need this
once in `configuration.yaml` (read it first; add it only if missing):

```yaml
homeassistant:
  packages: !include_dir_named packages
```

A package file (`packages/laundry.yaml`) holds any top-level integration keys:

```yaml
input_boolean:
  laundry_running:
    name: Laundry running
template:
  - sensor:
      - name: Laundry power
        unit_of_measurement: W
        state: "{{ states('sensor.washer_power') | float(0) }}"
```

Prefer UI-managed items (config item tools, helpers) when the user wants to edit them
in the UI; use packages for YAML-only integrations or when the user asks. After writing,
run `system` `check_config`; adding the `packages:` line needs a restart, new package
content usually needs a reload of that domain or a restart.

python_scripts run in a restricted sandbox (no imports). They need `python_script:` in
`configuration.yaml` and a restart once; then each `python_scripts/<name>.py` becomes the
action `python_script.<name>` (reload with `python_script.reload`). Inputs arrive in
`data`; `hass.services.call(domain, service, data)` calls actions; `logger` logs:

```python
entity_id = data.get("entity_id")
level = int(data.get("brightness", 128))
if entity_id:
    hass.services.call("light", "turn_on", {"entity_id": entity_id, "brightness": level})
    logger.info("Set %s to %s", entity_id, level)
```

Files are syntax-checked before saving. Prefer a script or template over a
python_script unless plain YAML can't do it.
