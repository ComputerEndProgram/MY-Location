"""Config flow for MY Location."""

import logging
import os
from typing import override

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_entry_oauth2_flow

from .const import (
    CONF_BRIDGE_SECRET,
    CONF_CLIENT_CERT,
    CONF_CLIENT_KEY,
    DEFAULT_CLIENT_CERT,
    DEFAULT_CLIENT_KEY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


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
            cert_path = (user_input.get(CONF_CLIENT_CERT) or "").strip()
            key_path = (user_input.get(CONF_CLIENT_KEY) or "").strip()

            if len(secret) < 32:
                errors["base"] = "bridge_secret_too_short"
            elif bool(cert_path) != bool(key_path):
                errors["base"] = "client_cert_pair_required"
            else:
                for name, path in (
                    (CONF_CLIENT_CERT, cert_path),
                    (CONF_CLIENT_KEY, key_path),
                ):
                    if path and not await self.hass.async_add_executor_job(
                        os.path.isfile, path
                    ):
                        errors[name] = "file_not_found"

            if not errors:
                options = {CONF_BRIDGE_SECRET: secret}
                if cert_path:
                    options[CONF_CLIENT_CERT] = cert_path
                    options[CONF_CLIENT_KEY] = key_path
                return self.async_create_entry(title="", data=options)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_BRIDGE_SECRET,
                        default=options.get(CONF_BRIDGE_SECRET, ""),
                    ): str,
                    vol.Optional(
                        CONF_CLIENT_CERT,
                        default=options.get(CONF_CLIENT_CERT, DEFAULT_CLIENT_CERT),
                    ): str,
                    vol.Optional(
                        CONF_CLIENT_KEY,
                        default=options.get(CONF_CLIENT_KEY, DEFAULT_CLIENT_KEY),
                    ): str,
                }
            ),
            errors=errors,
        )
