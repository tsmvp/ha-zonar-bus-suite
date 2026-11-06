"""Bus location trackers for Zonar Bus Suite.

One device_tracker per bus (assetName) the guardian's children ride. It carries
a GPS position while the driver has a route active, and goes unavailable
otherwise - matching how the app only shows the bus during an active run.
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


def _bus_names(data: dict) -> list[str]:
    return sorted({s["assetName"] for s in _student_stops(data) if s.get("assetName")})


async def async_setup_entry(
    hass: HomeAssistant, entry: ZonarConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        ZonarBusTracker(coordinator, name) for name in _bus_names(coordinator.data)
    )


class ZonarBusTracker(CoordinatorEntity[ZonarCoordinator], TrackerEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:bus-school"

    def __init__(self, coordinator: ZonarCoordinator, asset_name: str) -> None:
        super().__init__(coordinator)
        self._asset = asset_name
        self._attr_unique_id = f"{DOMAIN}_{asset_name}"
        self._attr_name = f"Bus {asset_name}"

    @property
    def _entry(self) -> dict | None:
        for bus in self.coordinator.data.get("buses") or []:
            if str(bus.get("assetName")) == str(self._asset):
                return bus
        return None

    @property
    def available(self) -> bool:
        return super().available and self._entry is not None

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        entry = self._entry
        value = entry.get("latitude") if entry else None
        return float(value) if value is not None else None

    @property
    def longitude(self) -> float | None:
        entry = self._entry
        value = entry.get("longitude") if entry else None
        return float(value) if value is not None else None

    @property
    def extra_state_attributes(self) -> dict:
        entry = self._entry or {}
        stops = [s for s in _student_stops(self.coordinator.data)
                 if str(s.get("assetName")) == str(self._asset)]
        return {
            "asset_name": self._asset,
            "heading": entry.get("heading"),
            "bearing": entry.get("bearing"),
            "direction": entry.get("direction"),
            "routes": sorted({s["route"] for s in stops if s.get("route")}),
            "runs": sorted({s["run"] for s in stops if s.get("run")}),
            "stops": [
                {
                    "name": s.get("stopName"),
                    "scheduled_time": s.get("scheduledTime"),
                    "type": s.get("routeStopType"),
                    "latitude": s.get("latitude"),
                    "longitude": s.get("longitude"),
                }
                for s in stops
            ],
        }
