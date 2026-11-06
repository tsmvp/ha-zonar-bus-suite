"""Data update coordinator for Zonar Bus Suite."""

from __future__ import annotations

import asyncio
import logging
import time

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ZonarApi, ZonarApiError, ZonarAuthError
from .const import DOMAIN, SCAN_INTERVAL, STUDENTS_MAX_AGE

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


class ZonarCoordinator(DataUpdateCoordinator):
    """Caches the student/run mapping; polls each run's live bus position."""

    def __init__(self, hass: HomeAssistant, api: ZonarApi) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.api = api
        self._students: dict | None = None
        self._students_ts = 0.0
        self._runs: list[str] = []

    async def _async_update_data(self) -> dict:
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
        except ZonarAuthError as err:
            raise ConfigEntryAuthFailed("Zonar login failed") from err
        except (ZonarApiError, Exception) as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err
        buses = [bus for run in results for bus in run]
        return {"buses": buses, "students": self._students}
