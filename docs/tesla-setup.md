# Tesla setup

This project uses Tesla's official Fleet API and Fleet Telemetry.

## Partner application

Create a Tesla developer application with the scopes required by the integration. The production setup used location/device-data access and Tesla OAuth handled by Home Assistant.

Never put the Tesla client secret in this repository.

## Partner domain and virtual key

Generate a P-256 EC keypair on the server. Keep the private key private and serve only the public key at Tesla's required partner-domain path:

```text
https://PARTNER_DOMAIN/.well-known/appspecific/com.tesla.3p.public-key.pem
```

The private key is subsequently used by the official Vehicle Command Proxy. Pair/enrol the corresponding virtual key with the vehicle using Tesla's supported flow.

## Partner registration

Obtain a partner token using the application's client credentials and register the partner domain with the regional Tesla Fleet API. Use the regional audience/API hostname appropriate to the Tesla account/vehicle.

Do not save partner tokens or client credentials in shell history, documentation, or Git.

## Telemetry configuration

MY Location's Configure telemetry action sends a deliberately small configuration through the Vehicle Command Proxy. The intended policy is:

```json
{
  "Location": {
    "interval_seconds": 2,
    "minimum_delta": 5
  }
}
```

The receiver hostname and port should point to the public Fleet Telemetry listener, e.g. `telemetry.example.com:4443`.

A vehicle may not adopt a new telemetry configuration until it is online. Once connected, the receiver should show connectivity records followed by `V` records containing `Location` while the vehicle moves.
