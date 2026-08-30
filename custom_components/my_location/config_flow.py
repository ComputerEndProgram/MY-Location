"""Config flow for MY Location."""

from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN


class OAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler,
    domain=DOMAIN,
):
    """Handle a MY Location config flow."""

    DOMAIN = DOMAIN

    async def async_oauth_create_entry(self, data: dict):
        """Create the config entry after successful OAuth."""
        return self.async_create_entry(title="MY Location", data=data)
