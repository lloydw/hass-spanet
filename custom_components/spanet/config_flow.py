"""Config flow for spanet integration."""
from __future__ import annotations

import logging
import uuid
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import OptionsFlowWithReload
from homeassistant.helpers.selector import (
    SelectSelector, SelectSelectorConfig, SelectSelectorMode,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .spanet import SpaNet, SpaNetAuthFailed
from .const import DOMAIN, OPT_ENABLE_HEAT_PUMP, SK_PUMPS
from .pump_options import (
    OPT_PUMP_CONTROL_MODES, OPT_PUMP_UNVERIFIED_CONFIRMATIONS,
    PUMP_CONTROL_AUTO, PUMP_CONTROL_SINGLE, PUMP_CONTROL_TWO_SPEED,
    pump_config_key, configured_mode,
)

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
        _LOGGER.debug("Validating SpaNET credentials")
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

class OptionsFlowHandler(OptionsFlowWithReload):
    """Per-pump controls alongside the existing heat-pump setting.

    Existing installs have no pump options: 'automatic' is implicit and
    mirrors Stage 4 behavior. OptionsFlowWithReload applies changes without
    requiring a full HA restart.
    """

    def __init__(self) -> None:
        self._pump_fields = {}
        self._pending_options = None
        self._pending_unverified = {}

    def _discover_pumps(self):
        """Map human-readable form labels to stable spa+number keys."""
        found = {}
        data = self.hass.data.get(DOMAIN, {})
        coordinators = data.get("spas", [])
        # If account contains multiple spas, names keep the form readable.
        for coordinator in coordinators:
            if coordinator.config_entry.entry_id != self.config_entry.entry_id:
                continue
            for number, pump in coordinator.state.get(SK_PUMPS, {}).items():
                key = pump_config_key(coordinator.spa_id, str(number))
                speeds = pump.get("speeds", 1)
                label = (
                    f"{coordinator.spa_name} — Pump {number} "
                    f"(detected: {speeds} speed{'s' if speeds != 1 else ''})"
                )
                # Preserve uniqueness if two device names are identical.
                if label in found:
                    label = f"{label} [{coordinator.spa_id}]"
                found[label] = (key, pump)
        # Also show saved overrides when a spa is temporarily offline.
        known = {key for key, _pump in found.values()}
        for key in (self.config_entry.options.get(OPT_PUMP_CONTROL_MODES) or {}):
            if key not in known:
                found[f"Saved pump {key} (currently unavailable)"] = (key, None)
        return found

    @staticmethod
    def _mode_selector():
        return SelectSelector(SelectSelectorConfig(
            options=[
                {"value": PUMP_CONTROL_AUTO,
                 "label": "Automatic detection (recommended)"},
                {"value": PUMP_CONTROL_SINGLE,
                 "label": "Standard On/Off switch only"},
                {"value": PUMP_CONTROL_TWO_SPEED,
                 "label": "Two-speed mode controls (Off / Auto / Low / High)"},
            ],
            mode=SelectSelectorMode.DROPDOWN,
        ))

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        return await self.async_step_settings(user_input)

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage heat pump and each available pump in one Configure screen."""
        if not self._pump_fields:
            self._pump_fields = self._discover_pumps()

        options = self.config_entry.options
        current_overrides = dict(options.get(OPT_PUMP_CONTROL_MODES) or {})
        confirmed = dict(options.get(OPT_PUMP_UNVERIFIED_CONFIRMATIONS) or {})
        defaults = {
            OPT_ENABLE_HEAT_PUMP: options.get(OPT_ENABLE_HEAT_PUMP, False)
        }
        for field, (key, _pump) in self._pump_fields.items():
            saved = current_overrides.get(key, PUMP_CONTROL_AUTO)
            defaults[field] = saved

        errors = {}
        if user_input is not None:
            next_overrides = dict(current_overrides)
            next_confirmed = dict(confirmed)
            unsupported = []
            unverified = {}
            for field, (key, pump) in self._pump_fields.items():
                selected = user_input.get(field, defaults[field])
                if selected == PUMP_CONTROL_AUTO:
                    next_overrides.pop(key, None)
                    next_confirmed.pop(key, None)
                else:
                    next_overrides[key] = selected
                    if selected != PUMP_CONTROL_TWO_SPEED:
                        next_confirmed.pop(key, None)
                    elif pump is None:
                        # Cannot safely change a forced mode while offline.
                        if not confirmed.get(key):
                            unsupported.append(field)
                    else:
                        try:
                            speeds = int(pump.get("speeds", 1))
                        except (ValueError, TypeError):
                            speeds = 1
                        if speeds == 2 and pump.get("hasSwitch"):
                            next_confirmed.pop(key, None)
                        elif speeds == 1 and pump.get("canSwitchOn"):
                            if not confirmed.get(key):
                                unverified[key] = field
                        else:
                            unsupported.append(field)

            if unsupported:
                errors["base"] = "unsupported_pump"
            else:
                saved = dict(options)
                saved[OPT_ENABLE_HEAT_PUMP] = user_input.get(
                    OPT_ENABLE_HEAT_PUMP, defaults[OPT_ENABLE_HEAT_PUMP]
                )
                saved[OPT_PUMP_CONTROL_MODES] = next_overrides
                saved[OPT_PUMP_UNVERIFIED_CONFIRMATIONS] = next_confirmed
                if unverified:
                    self._pending_options = saved
                    self._pending_unverified = unverified
                    return await self.async_step_confirm_two_speed()
                return self.async_create_entry(data=saved)

        schema_fields = {
            vol.Required(
                OPT_ENABLE_HEAT_PUMP,
                default=(user_input or {}).get(
                    OPT_ENABLE_HEAT_PUMP, defaults[OPT_ENABLE_HEAT_PUMP]
                ),
            ): bool,
        }
        for field in self._pump_fields:
            schema_fields[vol.Required(
                field, default=(user_input or {}).get(field, defaults[field])
            )] = self._mode_selector()
        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(schema_fields),
            errors=errors,
        )

    async def async_step_confirm_two_speed(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Require informed consent before enabling unverified speed commands."""
        if self._pending_options is None:
            return await self.async_step_settings()

        if user_input is not None and user_input.get("acknowledge_unverified"):
            opts = self._pending_options
            confirmed = dict(opts.get(OPT_PUMP_UNVERIFIED_CONFIRMATIONS) or {})
            for key in self._pending_unverified:
                confirmed[key] = True
            opts[OPT_PUMP_UNVERIFIED_CONFIRMATIONS] = confirmed
            return self.async_create_entry(data=opts)

        errors = {"base": "confirmation_required"} if user_input is not None else {}
        return self.async_show_form(
            step_id="confirm_two_speed",
            data_schema=vol.Schema({
                vol.Required("acknowledge_unverified", default=False): bool,
            }),
            errors=errors,
            description_placeholders={
                "pumps": ", ".join(self._pending_unverified.values())
            },
        )
