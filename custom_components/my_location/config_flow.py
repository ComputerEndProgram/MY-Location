"""Config flow for MY Location."""

from homeassistant import config_entries
from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN, OAUTH_SCOPES, REDIRECT_URI


class OAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler,
    domain=DOMAIN,
):
    """Handle a MY Location config flow."""

    DOMAIN = DOMAIN

    @property
    def logger(self):
        """Return logger."""
        return __import__("logging").getLogger(__name__)

    @property
    def extra_authorize_data(self) -> dict[str, str]:
        """Return Tesla OAuth authorization parameters."""
        return {
            "scope": " ".join(OAUTH_SCOPES),
            "redirect_uri": REDIRECT_URI,
            "prompt": "login",
        }

    async def async_oauth_create_entry(self, data: dict):
        """Create the config entry after successful OAuth."""
        return self.async_create_entry(title="MY Location", data=data)
