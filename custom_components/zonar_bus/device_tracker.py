"""Bus location trackers for Zonar Bus Suite.

One device_tracker per run (routeMasterTypeXid) the guardian's children ride.
It carries a GPS position while the driver has that route active, and goes
unavailable otherwise - matching how the app only shows the bus during a run.
"""

from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ZonarConfigEntry
from .const import DOMAIN
from .coordinator import ZonarCoordinator


def _student_stops(data: dict) -> list[dict]:
    return (data.get("students") or {}).get("studentStops") or []


def _runs(data: dict) -> dict[str, dict]:
    """Map each run (routeMasterTypeXId) to display info from studentStops."""
    runs: dict[str, dict] = {}
    for stop in _student_stops(data):
        rmtx = stop.get("routeMasterTypeXId")
        if rmtx and rmtx not in runs:
            runs[rmtx] = {
                "route": stop.get("route"),
                "routeType": stop.get("routeType"),
                "assetName": stop.get("assetName"),
            }
    return runs


async def async_setup_entry(
    hass: HomeAssistant, entry: ZonarConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        ZonarBusTracker(coordinator, rmtx, info) for rmtx, info in _runs(coordinator.data).items()
    )


class ZonarBusTracker(CoordinatorEntity[ZonarCoordinator], TrackerEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:bus-school"

    def __init__(self, coordinator: ZonarCoordinator, rmtx: str, info: dict) -> None:
        super().__init__(coordinator)
        self._rmtx = rmtx
        self._info = info
        self._attr_unique_id = f"{DOMAIN}_{rmtx}"
        self._attr_name = info.get("route") or f"Bus {info.get('assetName') or rmtx}"

    @property
    def _bus(self) -> dict | None:
        # Live objects key the run as "routeMasterTypeXid" (lower-case id).
        for bus in self.coordinator.data.get("buses") or []:
            if str(bus.get("routeMasterTypeXid")) == str(self._rmtx):
                return bus
        return None

    @property
    def available(self) -> bool:
        return super().available and self._bus is not None

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        bus = self._bus
        loc = bus.get("location") if bus else None
        return float(loc["x"]) if loc and loc.get("x") is not None else None

    @property
    def longitude(self) -> float | None:
        bus = self._bus
        loc = bus.get("location") if bus else None
        return float(loc["y"]) if loc and loc.get("y") is not None else None

    @property
    def extra_state_attributes(self) -> dict:
        bus = self._bus or {}
        stops = [
            s for s in _student_stops(self.coordinator.data)
            if str(s.get("routeMasterTypeXId")) == str(self._rmtx)
        ]
        return {
            "asset_name": bus.get("assetName") or self._info.get("assetName"),
            "route": bus.get("route") or self._info.get("route"),
            "route_type": bus.get("routeType") or self._info.get("routeType"),
            "heading": bus.get("heading"),
            "route_xid": bus.get("routeXid"),
            "stops": [
                {
                    "name": s.get("stopName"),
                    "scheduled_time": s.get("scheduledTime"),
                    "type": s.get("routeStopType"),
                    "pickup_or_dropoff": s.get("pickupOrDropOff"),
                    "latitude": s.get("latitude"),
                    "longitude": s.get("longitude"),
                }
                for s in stops
            ],
        }
