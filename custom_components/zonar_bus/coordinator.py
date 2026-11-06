"""Data update coordinator for Zonar Bus Suite."""

from __future__ import annotations

import logging
import time

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ZonarApi, ZonarApiError, ZonarAuthError
from .const import DOMAIN, SCAN_INTERVAL, STUDENTS_MAX_AGE

_LOGGER = logging.getLogger(__name__)


class ZonarCoordinator(DataUpdateCoordinator):
    """Polls assetLocation; keeps the student/route mapping cached."""

    def __init__(self, hass: HomeAssistant, api: ZonarApi) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.api = api
        self._students: dict | None = None
        self._students_ts = 0.0

    async def _async_update_data(self) -> dict:
        try:
            now = time.monotonic()
            if self._students is None or now - self._students_ts > STUDENTS_MAX_AGE:
                await self.api.current_user()
                self._students = await self.api.students()
                self._students_ts = now
            buses = await self.api.asset_locations()
        except ZonarAuthError as err:
            raise ConfigEntryAuthFailed("Zonar login failed") from err
        except (ZonarApiError, Exception) as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err
        return {"buses": buses, "students": self._students}
