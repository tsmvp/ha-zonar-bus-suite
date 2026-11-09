# Zonar Bus Suite (Home Assistant)

Track your child's school bus from the Zonar Bus Suite Parent app in Home
Assistant. Creates a single `device_tracker.school_bus` that follows whichever
run is currently active (morning or afternoon), plus a `sensor.school_bus_status`
tile. The tracker shows live GPS while the driver has a route active and goes
unavailable otherwise; the status sensor stays visible and reads
`Not running` / `En route (AM)` / `En route (PM)`.

## Install

1. Copy `custom_components/zonar_bus/` into your Home Assistant `config/custom_components/` folder (or add this repo to HACS as a custom repository).
2. Restart Home Assistant.
3. Settings -> Devices & Services -> Add Integration -> "Zonar Bus Suite".
4. Sign in with the same email/phone and password you use in the app.

You get two always-present entities: `device_tracker.school_bus` (the live GPS
marker for the active run) and `sensor.school_bus_status`. Tracker attributes
include `route`, `route_type` (AM/PM), `heading`, `asset_name`, and the child's
`stop_name` / `scheduled_time` / `stop_latitude` / `stop_longitude`.

## Stops on the map

While a run is active, each stop on that route is added as its own numbered
`device_tracker` (`Bus stop 1 …`, `Bus stop 2 …`, with a `mdi:numeric-N-circle`
icon), so the Map card shows the stops around the moving bus. Your own child's
stop is drawn distinctly (a boxed number, `is_my_stop: true`). Stops appear only
for the active route and go unavailable between runs, same as the bus.

A simple Map card that shows the bus and its stops together:

```yaml
type: map
entities:
  - device_tracker.school_bus
# stop markers share the `zonar_bus` naming; add them as they appear, or use
# an auto-entities card filtered to `device_tracker.bus_stop_*`.
hours_to_show: 0
```

The numbered-circle icons render most reliably with the HACS
[ha-map-card](https://github.com/nathan-gs/ha-map-card) (`custom:map-card`),
which also draws the translucent **route line** (see below).

## How it works

- Logs in to `authapi.bus-suite.com` (120-day token, auto re-login on expiry).
- Reads your organization and children from `bussuite-gapi.zonar.com`
  (`currentUserInfo`, `students`). `students` also lists each child's runs
  (`routeMasterTypeXid`), buses, and stops.
- Polls `GET /ga/assetLocation/{routeMasterTypeXid}` every 15s for each run,
  but only inside the run windows in `schedule.py` (weekdays 06:30-08:45,
  Wednesday until 09:45, and 15:15-18:30, local time). Outside them Zonar is
  not called and the bus reads `Not running`, so the map starts clean each run.
  The response carries the position as `location.x` (latitude) / `location.y`
  (longitude) plus `heading` and `assetName`.

- For the active run it fetches the route's ordered stops once
  (`GET /ga/routePlan/stops/{routeXid}`, cached) and exposes each as a numbered
  marker, matching your child's stop by `routeStopXid`.

Each run only returns a position once the **driver marks the route active** -
until then the tracker is `unavailable`. That is expected, not a fault.

## Route line

`sensor.school_bus_route` carries the active route's road path as a GeoJSON
`LineString` in its `route_geojson` attribute (built from
`GET /ga/routePlan/waypoints/{routeXid}`, downsampled to ~500 points so the
attribute stays small). Its state is the route name, or `Idle` between runs.

The stock Map card cannot draw a line, so use the HACS
[ha-map-card](https://github.com/nathan-gs/ha-map-card). One card then shows the
bus, the numbered stops, and the translucent route path:

```yaml
type: custom:map-card
x: 45.34039          # centre near your stop
y: -75.70167
zoom: 13
entities:
  - entity: device_tracker.school_bus
  - entity: sensor.school_bus_route
    display: geojson
    geojson:
      attribute: route_geojson
      color: "#2196F3"
      weight: 4
      opacity: 0.4       # translucent route line
      hide_marker: true
  # numbered stops appear as device_tracker.bus_stop_* while a run is active;
  # list them here, or use an auto-entities card to include them automatically.
```

## Example automation: notify when the bus is near the stop

```yaml
automation:
  - alias: Bus approaching stop
    trigger:
      - trigger: state
        entity_id: device_tracker.school_bus
    condition:
      - condition: template
        value_template: >
          {{ state_attr('device_tracker.school_bus', 'latitude') is not none and
             state_attr('device_tracker.school_bus', 'stop_latitude') is not none and
             distance('device_tracker.school_bus',
                      state_attr('device_tracker.school_bus', 'stop_latitude'),
                      state_attr('device_tracker.school_bus', 'stop_longitude')) < 0.5 }}
    action:
      - action: notify.family
        data:
          message: "The school bus is less than 500 m from the stop."
```

## Disclaimer

Unofficial, for personal/family use. Uses your own account via the same API the
app uses. Not affiliated with Zonar or ezEnroute.
