"""Data update coordinator for Zonar Bus Suite."""

from __future__ import annotations

import asyncio
import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import ZonarApi, ZonarApiError, ZonarAuthError
from .const import DOMAIN, SCAN_INTERVAL, STUDENTS_MAX_AGE
from .schedule import in_run_window

_LOGGER = logging.getLogger(__name__)


def route_master_type_xids(students: dict | None) -> list[str]:
    """The run identifiers (routeMasterTypeXId) for the guardian's children."""
    stops = (students or {}).get("studentStops") or []
    return sorted({s["routeMasterTypeXId"] for s in stops if s.get("routeMasterTypeXId")})


def active_bus(data: dict | None) -> dict | None:
    """The currently-active run's bus, or None when nothing is running."""
    buses = (data or {}).get("buses") or []
    return buses[0] if buses else None


def run_stops(data: dict | None, rmtx: str | None) -> list[dict]:
    """The child's stops for a given run (routeMasterTypeXId)."""
    stops = ((data or {}).get("students") or {}).get("studentStops") or []
    return [s for s in stops if rmtx and str(s.get("routeMasterTypeXId")) == str(rmtx)]


def my_stop_xids(students: dict | None) -> set[str]:
    """routeStopXids that belong to the guardian's children."""
    stops = (students or {}).get("studentStops") or []
    return {s.get("routeStopXid") for s in stops if s.get("routeStopXid")}


def route_xid_for_bus(bus: dict, students: dict | None) -> str | None:
    """The routeXid for an active bus; falls back to the studentStops mapping."""
    if bus.get("routeXid"):
        return bus["routeXid"]
    rmtx = bus.get("routeMasterTypeXid")
    for s in (students or {}).get("studentStops") or []:
        if str(s.get("routeMasterTypeXId")) == str(rmtx):
            return s.get("routeXid")
    return None


def _stop_marker(raw: dict, mine: set[str]) -> dict:
    """Flatten a route-plan stop into the marker fields the entities use."""
    loc = raw.get("stopLocationG") or {}
    xid = raw.get("routeStopXid")
    try:
        number = int(raw.get("stopNumber") or raw.get("pathOrder") or 0)
    except (TypeError, ValueError):
        number = 0
    return {
        "routeStopXid": xid,
        "number": number,
        "name": raw.get("stopName"),
        "address": raw.get("stopAddress"),
        "scheduled_time": raw.get("scheduledTime"),
        "latitude": loc.get("lat"),
        "longitude": loc.get("lng"),
        "is_my_stop": xid in mine,
    }


class ZonarCoordinator(DataUpdateCoordinator):
    """Caches the student/run mapping; polls each run's live bus position."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: ZonarApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
            config_entry=entry,
        )
        self.api = api
        self._students: dict | None = None
        self._students_ts = 0.0
        self._runs: list[str] = []
        self._stops_cache: dict[str, list] = {}  # routeXid -> route-plan stops (static)

    async def _async_update_data(self) -> dict:
        # Outside a run window, skip Zonar and report no bus, so the tracker
        # clears instead of holding the last position until the next run.
        if not in_run_window(dt_util.now()):
            return {"buses": [], "students": self._students, "stops": []}
        try:
            now = time.monotonic()
            if self._students is None or now - self._students_ts > STUDENTS_MAX_AGE:
                await self.api.current_user()
                self._students = await self.api.students()
                self._students_ts = now
                self._runs = route_master_type_xids(self._students)
            results = await asyncio.gather(
                *(self.api.asset_location(rmtx) for rmtx in self._runs)
            )
            buses = [bus for run in results for bus in run]
            stops = await self._active_route_stops(buses[0]) if buses else []
        except ZonarAuthError as err:
            raise ConfigEntryAuthFailed("Zonar login failed") from err
        except (ZonarApiError, Exception) as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err
        return {"buses": buses, "students": self._students, "stops": stops}

    async def _active_route_stops(self, bus: dict) -> list[dict]:
        """Numbered stop markers for the active run's route (cached per routeXid)."""
        route_xid = route_xid_for_bus(bus, self._students)
        if not route_xid:
            return []
        if route_xid not in self._stops_cache:
            self._stops_cache[route_xid] = await self.api.route_stops(route_xid)
        mine = my_stop_xids(self._students)
        return [
            _stop_marker(s, mine)
            for s in self._stops_cache[route_xid]
            if s.get("showOnMap", True)
            and (s.get("stopLocationG") or {}).get("lat") is not None
        ]
