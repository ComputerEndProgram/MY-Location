"""Application credentials support for MY Location."""

from typing import Any, override

from homeassistant.components.application_credentials import ClientCredential
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import LocalOAuth2Implementation

from .const import (
    AUTHORIZE_URL,
    FLEET_API_BASE,
    OAUTH_SCOPES,
    REDIRECT_URI,
    TOKEN_URL,
)


class TeslaOAuth2Implementation(LocalOAuth2Implementation):
    """Tesla-specific OAuth implementation."""

    def __init__(
        self,
        hass: HomeAssistant,
        auth_domain: str,
        credential: ClientCredential,
    ) -> None:
        """Initialize Tesla OAuth."""
        super().__init__(
            hass,
            auth_domain,
            credential.client_id,
            credential.client_secret,
            AUTHORIZE_URL,
            TOKEN_URL,
        )
        self._name = credential.name

    @property
    @override
    def name(self) -> str:
        """Return the application credential name."""
        return self._name or self.client_id

    @property
    @override
    def redirect_uri(self) -> str:
        """Use the callback URL registered in the Tesla developer application."""
        return REDIRECT_URI

    @property
    @override
    def extra_authorize_data(self) -> dict[str, Any]:
        """Return Tesla authorization parameters."""
        return {
            "scope": " ".join(OAUTH_SCOPES),
            "prompt": "login",
            "prompt_missing_scopes": "true",
            "require_requested_scopes": "true",
        }

    @property
    @override
    def extra_token_resolve_data(self) -> dict[str, Any]:
        """Return Tesla token-exchange parameters."""
        return {"audience": FLEET_API_BASE}


async def async_get_auth_implementation(
    hass: HomeAssistant,
    auth_domain: str,
    credential: ClientCredential,
) -> TeslaOAuth2Implementation:
    """Return the Tesla OAuth implementation."""
    return TeslaOAuth2Implementation(hass, auth_domain, credential)
