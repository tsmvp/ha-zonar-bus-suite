"""Status sensor for Zonar Bus Suite.

An always-available tile showing whether the bus is running and, when it is,
the active route (AM/PM), the child's stop, and the scheduled time.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ZonarConfigEntry
from .const import DOMAIN
from .coordinator import ZonarCoordinator, active_bus, run_stops


async def async_setup_entry(
    hass: HomeAssistant, entry: ZonarConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            ZonarBusStatusSensor(coordinator, entry.entry_id),
            ZonarRouteSensor(coordinator, entry.entry_id),
        ]
    )


class ZonarBusStatusSensor(CoordinatorEntity[ZonarCoordinator], SensorEntity):
    _attr_name = "School bus status"
    _attr_icon = "mdi:bus-clock"

    def __init__(self, coordinator: ZonarCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_status"

    @property
    def native_value(self) -> str:
        bus = active_bus(self.coordinator.data)
        if not bus:
            return "Not running"
        route_type = bus.get("routeType")
        return f"En route ({route_type})" if route_type else "En route"

    @property
    def extra_state_attributes(self) -> dict:
        bus = active_bus(self.coordinator.data) or {}
        loc = bus.get("location") or {}
        stops = run_stops(self.coordinator.data, bus.get("routeMasterTypeXid"))
        stop = stops[0] if stops else {}
        return {
            "route": bus.get("route"),
            "route_type": bus.get("routeType"),
            "asset_name": bus.get("assetName"),
            "heading": bus.get("heading"),
            "latitude": loc.get("x"),
            "longitude": loc.get("y"),
            "stop_name": stop.get("stopName"),
            "scheduled_time": stop.get("scheduledTime"),
        }


class ZonarRouteSensor(CoordinatorEntity[ZonarCoordinator], SensorEntity):
    """Carries the active route's path as a GeoJSON LineString for the map.

    Draw it with the HACS ha-map-card: add this entity with
    `geojson: {attribute: route_geojson, opacity: 0.4, hide_marker: true}`.
    """

    _attr_name = "School bus route"
    _attr_icon = "mdi:map-marker-path"

    def __init__(self, coordinator: ZonarCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_route"

    @property
    def native_value(self) -> str:
        return (self.coordinator.data or {}).get("route_name") or "Idle"

    @property
    def extra_state_attributes(self) -> dict:
        geojson = (self.coordinator.data or {}).get("route_geojson")
        coords = (geojson or {}).get("geometry", {}).get("coordinates") or []
        start = coords[0] if coords else [None, None]
        return {
            "route_geojson": geojson,
            "points": len(coords),
            # a location on the route so the map card can place the (hidden) entity
            "latitude": start[1],
            "longitude": start[0],
        }
