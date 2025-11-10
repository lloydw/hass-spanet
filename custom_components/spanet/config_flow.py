"""Config flow for spanet integration."""
from __future__ import annotations

import logging
import uuid
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .spanet import SpaNet, SpaNetAuthFailed
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for spanet."""

    VERSION = 1
    STEP_USER_DATA_SCHEMA = vol.Schema(
        {
            vol.Required("email"): str,
            vol.Required("password"): str,
        }
    )


    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=ConfigFlow.STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await ConfigFlow.validate_input(self.hass, user_input)
        except SpaNetAuthFailed:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
        """Validate the user input allows us to connect.

        Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
        """

        session = aiohttp_client.async_get_clientsession(hass)
        spanet = SpaNet(session)
        _LOGGER.debug(f"Validate - {data['email']} {data['password']}")
        try:
            await spanet.authenticate(data["email"], data["password"], str(uuid.uuid4()))
        except Exception as e:
            _LOGGER.info(e)
            raise
        return {"title": "SpaNET"}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler()

class OptionsFlowHandler(config_entries.OptionsFlow):

    SETTINGS_SCHEMA=vol.Schema(
        {
            vol.Required("enable_heat_pump", default=False): bool,
        }
    )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return await self.async_step_settings(user_input)

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""

        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="settings",
            data_schema=self.add_suggested_values_to_schema(
                OptionsFlowHandler.SETTINGS_SCHEMA, self.config_entry.options
            )
        )
