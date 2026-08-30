"""Application credentials support for MY Location."""

from typing import Any, override

from homeassistant.components.application_credentials import (
    AuthImplementation,
    AuthorizationServer,
    ClientCredential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow

from .const import (
    AUTHORIZE_URL,
    FLEET_API_BASE,
    OAUTH_SCOPES,
    REDIRECT_URI,
    TOKEN_URL,
)


class TeslaOAuth2Implementation(AuthImplementation):
    """Tesla-specific OAuth implementation."""

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
) -> config_entry_oauth2_flow.AbstractOAuth2Implementation:
    """Return the Tesla OAuth implementation."""
    return TeslaOAuth2Implementation(
        hass=hass,
        auth_domain=auth_domain,
        credential=credential,
        authorization_server=await async_get_authorization_server(hass),
    )


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return Tesla's OAuth authorization server."""
    return AuthorizationServer(
        authorize_url=AUTHORIZE_URL,
        token_url=TOKEN_URL,
    )
