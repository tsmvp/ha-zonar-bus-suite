"""Config flow for Zonar Bus Suite (email/phone + password)."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ZonarApi, ZonarAuthError
from .const import DOMAIN

STEP_USER = vol.Schema({vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str})


class ZonarConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = ZonarApi(session, user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
            try:
                await api.login()
                await api.current_user()
            except ZonarAuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_USERNAME], data=user_input)
        return self.async_show_form(step_id="user", data_schema=STEP_USER, errors=errors)
