# Zonar Bus Suite (Home Assistant)

Track your child's school bus from the Zonar Bus Suite Parent app in Home
Assistant. Creates a `device_tracker` per bus that shows live GPS while a route
is active and goes unavailable otherwise.

## Install

1. Copy `custom_components/zonar_bus/` into your Home Assistant `config/custom_components/` folder (or add this repo to HACS as a custom repository).
2. Restart Home Assistant.
3. Settings -> Devices & Services -> Add Integration -> "Zonar Bus Suite".
4. Sign in with the same email/phone and password you use in the app.

A tracker named `device_tracker.bus_<name>` is created for each bus your
children ride. Attributes include `heading`, `bearing`, `direction`, the
`routes`/`runs`, and each `stop` (name, scheduled time, coordinates).

## How it works

- Logs in to `authapi.bus-suite.com` (120-day token, auto re-login on expiry).
- Reads your organization and children from `bussuite-gapi.zonar.com`
  (`currentUserInfo`, `students`).
- Polls `/ga/assetLocation` every 30s for live bus positions.

Buses only report coordinates once the **driver marks the route active** - until
then the tracker is `unavailable`. That is expected, not a fault.

## Example automation: notify when the bus is near the stop

```yaml
automation:
  - alias: Bus approaching stop
    trigger:
      - trigger: state
        entity_id: device_tracker.bus_123   # your bus entity
    condition:
      - condition: template
        value_template: >
          {{ state_attr('device_tracker.bus_123','latitude') is not none and
             distance(states('device_tracker.bus_123'),
                      state_attr('device_tracker.bus_123','stops')[0].latitude,
                      state_attr('device_tracker.bus_123','stops')[0].longitude) < 0.5 }}
    action:
      - action: notify.family
        data:
          message: "The school bus is less than 500 m from the stop."
```

## Verify / one tweak that may be needed

The tracker matches a live bus to your child by the `assetName` field in the
`/ga/assetLocation` response. That field list was read from the app
(`latitude, longitude, heading, bearing, direction, assetName`) but has not yet
been seen with a live, active route. When a bus is running, check the tracker's
attributes; if `latitude`/`longitude` stay empty while the app shows the bus,
the live object uses different key names and `device_tracker.py` needs those key
names updated (one small edit in the `_entry`/`latitude`/`longitude` properties).

## Disclaimer

Unofficial, for personal/family use. Uses your own account via the same API the
app uses. Not affiliated with Zonar or ezEnroute.
