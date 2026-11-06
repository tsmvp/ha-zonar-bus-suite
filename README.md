# Zonar Bus Suite (Home Assistant)

Track your child's school bus from the Zonar Bus Suite Parent app in Home
Assistant. Creates a `device_tracker` per bus run that shows live GPS while the
driver has the route active, and goes unavailable otherwise.

## Install

1. Copy `custom_components/zonar_bus/` into your Home Assistant `config/custom_components/` folder (or add this repo to HACS as a custom repository).
2. Restart Home Assistant.
3. Settings -> Devices & Services -> Add Integration -> "Zonar Bus Suite".
4. Sign in with the same email/phone and password you use in the app.

A tracker is created for each run your children ride (e.g. "Route 5 PM WK1
Nepean/Alta Vista"). Attributes include `asset_name`, `route_type`, `heading`,
`route_xid`, and each `stop` (name, scheduled time, pickup/drop-off, coords).

## How it works

- Logs in to `authapi.bus-suite.com` (120-day token, auto re-login on expiry).
- Reads your organization and children from `bussuite-gapi.zonar.com`
  (`currentUserInfo`, `students`). `students` also lists each child's runs
  (`routeMasterTypeXid`), buses, and stops.
- Polls `GET /ga/assetLocation/{routeMasterTypeXid}` every 30s for each run.
  The response carries the position as `location.x` (latitude) / `location.y`
  (longitude) plus `heading` and `assetName`.

Each run only returns a position once the **driver marks the route active** -
until then the tracker is `unavailable`. That is expected, not a fault.

## Example automation: notify when the bus is near the stop

```yaml
automation:
  - alias: Bus approaching stop
    trigger:
      - trigger: state
        entity_id: device_tracker.route_5_pm_wk1_nepean_alta_vista   # your entity
    condition:
      - condition: template
        value_template: >
          {% set s = state_attr(trigger.entity_id, 'stops') %}
          {{ state_attr(trigger.entity_id, 'latitude') is not none and s
             and distance(states(trigger.entity_id),
                          s[0].latitude, s[0].longitude) < 0.5 }}
    action:
      - action: notify.family
        data:
          message: "The school bus is less than 500 m from the stop."
```

## Disclaimer

Unofficial, for personal/family use. Uses your own account via the same API the
app uses. Not affiliated with Zonar or ezEnroute.
