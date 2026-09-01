"""Config flow for MY Location."""

import logging
from typing import override

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_BRIDGE_SECRET = "bridge_secret"


class OAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler,
    domain=DOMAIN,
):
    """Handle a MY Location config flow."""

    DOMAIN = DOMAIN

    @property
    @override
    def logger(self) -> logging.Logger:
        """Return the integration logger."""
        return _LOGGER

    async def async_oauth_create_entry(self, data: dict):
        """Create the config entry after successful OAuth."""
        return self.async_create_entry(title="Tesla Fleet", data=data)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return MyLocationOptionsFlow()


class MyLocationOptionsFlow(config_entries.OptionsFlow):
    """Configure the secure Fleet Telemetry bridge."""

    async def async_step_init(self, user_input=None):
        """Manage MY Location options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            secret = user_input[CONF_BRIDGE_SECRET].strip()
            if len(secret) < 32:
                errors["base"] = "bridge_secret_too_short"
            else:
                return self.async_create_entry(
                    title="",
                    data={CONF_BRIDGE_SECRET: secret},
                )

        current = self.config_entry.options.get(CONF_BRIDGE_SECRET, "")
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_BRIDGE_SECRET,
                        default=current,
                    ): str
                }
            ),
            errors=errors,
        )
