DOMAIN = "my_location"

AUTHORIZE_URL = "https://auth.tesla.com/oauth2/v3/authorize"
TOKEN_URL = "https://fleet-auth.prd.vn.cloud.tesla.com/oauth2/v3/token"
FLEET_API_BASE = "https://fleet-api.prd.eu.vn.cloud.tesla.com"
REDIRECT_URI = "https://homeassistant.lcars.qzz.io/auth/external/callback"

OAUTH_SCOPES = [
    "openid",
    "offline_access",
    "vehicle_device_data",
    "vehicle_location",
]
