"""Bus and stop trackers for Zonar Bus Suite.

- One `School bus` tracker follows whichever run is active, with a GPS position
  while the driver has a route active and unavailable otherwise.
- One numbered marker per stop on the active route (added the first time a run
  goes active), so the Map card shows the stops around the moving bus. The
  guardian's own stop is drawn distinctly.
"""

from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ZonarConfigEntry
from .const import DOMAIN
from .coordinator import ZonarCoordinator, active_bus, run_stops


async def async_setup_entry(
    hass: HomeAssistant, entry: ZonarConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([ZonarBusTracker(coordinator, entry.entry_id)])

    known: set[str] = set()

    @callback
    def _add_new_stops() -> None:
        new = []
        for stop in (coordinator.data or {}).get("stops") or []:
            xid = stop.get("routeStopXid")
            if xid and xid not in known:
                known.add(xid)
                new.append(ZonarBusStopTracker(coordinator, entry.entry_id, stop))
        if new:
            async_add_entities(new)

    _add_new_stops()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_stops))


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


class ZonarBusStopTracker(CoordinatorEntity[ZonarCoordinator], TrackerEntity):
    """A single numbered stop on the active route; plotted while the run is active."""

    def __init__(self, coordinator: ZonarCoordinator, entry_id: str, snapshot: dict) -> None:
        super().__init__(coordinator)
        self._xid = snapshot["routeStopXid"]
        self._mine = snapshot.get("is_my_stop", False)
        n = snapshot.get("number") or 0
        base = snapshot.get("name") or (f"Stop {n}" if n else "Stop")
        name = f"Bus stop {n} - {base}" if n else f"Bus stop - {base}"
        self._attr_name = f"{name} (your stop)" if self._mine else name
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_stop_{self._xid}"
        if 1 <= n <= 9:
            self._attr_icon = f"mdi:numeric-{n}-box" if self._mine else f"mdi:numeric-{n}-circle"
        else:
            self._attr_icon = "mdi:home-map-marker" if self._mine else "mdi:bus-stop"

    @property
    def _stop(self) -> dict | None:
        for s in (self.coordinator.data or {}).get("stops") or []:
            if s.get("routeStopXid") == self._xid:
                return s
        return None

    @property
    def available(self) -> bool:
        return super().available and self._stop is not None

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        s = self._stop
        return float(s["latitude"]) if s and s.get("latitude") is not None else None

    @property
    def longitude(self) -> float | None:
        s = self._stop
        return float(s["longitude"]) if s and s.get("longitude") is not None else None

    @property
    def extra_state_attributes(self) -> dict:
        s = self._stop or {}
        return {
            "stop_number": s.get("number"),
            "scheduled_time": s.get("scheduled_time"),
            "address": s.get("address"),
            "is_my_stop": self._mine,
        }
