"""Single bus tracker for Zonar Bus Suite.

One device_tracker that follows whichever run is currently active (morning or
afternoon). It carries a GPS position while the driver has a route active and
goes unavailable otherwise.
"""

from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ZonarConfigEntry
from .const import DOMAIN
from .coordinator import ZonarCoordinator, active_bus, run_stops


async def async_setup_entry(
    hass: HomeAssistant, entry: ZonarConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([ZonarBusTracker(entry.runtime_data, entry.entry_id)])


class ZonarBusTracker(CoordinatorEntity[ZonarCoordinator], TrackerEntity):
    _attr_name = "School bus"
    _attr_icon = "mdi:bus-school"

    def __init__(self, coordinator: ZonarCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_bus"

    @property
    def _bus(self) -> dict | None:
        return active_bus(self.coordinator.data)

    @property
    def available(self) -> bool:
        return super().available and self._bus is not None

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        loc = (self._bus or {}).get("location")
        return float(loc["x"]) if loc and loc.get("x") is not None else None

    @property
    def longitude(self) -> float | None:
        loc = (self._bus or {}).get("location")
        return float(loc["y"]) if loc and loc.get("y") is not None else None

    @property
    def extra_state_attributes(self) -> dict:
        bus = self._bus or {}
        stops = run_stops(self.coordinator.data, bus.get("routeMasterTypeXid"))
        stop = stops[0] if stops else {}
        return {
            "route": bus.get("route"),
            "route_type": bus.get("routeType"),
            "asset_name": bus.get("assetName"),
            "heading": bus.get("heading"),
            "stop_name": stop.get("stopName"),
            "scheduled_time": stop.get("scheduledTime"),
            "pickup_or_dropoff": stop.get("pickupOrDropOff"),
            "stop_latitude": stop.get("latitude"),
            "stop_longitude": stop.get("longitude"),
        }
