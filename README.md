# MY Location

A minimal Home Assistant custom integration that turns Tesla Fleet Telemetry location data into a native `device_tracker` — without TeslaMate or MQTT.

## What it does

MY Location uses Tesla's official Fleet API/Fleet Telemetry infrastructure. Home Assistant handles Tesla OAuth and exposes a narrow webhook. A small receiver stack on a public Linux server accepts the vehicle's mTLS telemetry stream and forwards only location data to Home Assistant.

The intended use case is zone-based automation such as garage-door arrival/departure logic, while avoiding continuous Fleet API polling.

## Architecture

```text
Tesla vehicle
    |
    | Fleet Telemetry over mTLS (Location only)
    v
Public VPS :4443
    |
    | tesla/fleet-telemetry
    v
Docker syslog -> 127.0.0.1:5514/UDP
    |
    | receiver/bridge.py
    v
HTTPS Home Assistant webhook
    |
    v
MY Location integration
    |
    v
device_tracker -> HA zones / automations
```

The Tesla Vehicle Command Proxy is also run on the VPS, but is bound to `127.0.0.1` only. It is used to sign Fleet Telemetry configuration requests with the enrolled virtual-key private key.

## Current telemetry policy

The production configuration is intentionally minimal:

```json
"Location": {
  "interval_seconds": 2,
  "minimum_delta": 5
}
```

This requests location updates at most every two seconds and suppresses updates until the vehicle has moved roughly five metres. No TeslaMate-style database is required and the bridge discards non-location telemetry.

## Documentation

- [Architecture and security](docs/architecture.md)
- [Tesla setup](docs/tesla-setup.md)
- [VPS/server setup](docs/server-setup.md)
- [Home Assistant setup](docs/home-assistant.md)
- [Certificate renewal](docs/certificate-renewal.md)
- [Troubleshooting](docs/troubleshooting.md)

Reusable deployment examples are in [`server/`](server/).

## HACS installation

1. Add `ComputerEndProgram/MY-Location` to HACS as a custom repository of type **Integration**.
2. Install **MY Location** and restart Home Assistant.
3. Configure the Tesla application credentials in Home Assistant.
4. Add the **MY Location** integration and complete Tesla OAuth.
5. Configure a long random Fleet Telemetry bridge secret in the integration options.
6. Deploy the VPS receiver as documented in `docs/server-setup.md`.
7. Use **Configure telemetry** in the MY Location integration to send the Fleet Telemetry configuration to the vehicle.

## Security

Never commit or publish:

- Tesla client secrets
- OAuth access/refresh tokens
- webhook secrets
- full VINs
- virtual-key private keys
- TLS private keys

The examples use placeholders for site-specific hostnames, IP addresses and secrets. The public Fleet Telemetry listener requires mTLS. The Vehicle Command Proxy and UDP bridge are localhost-only.

## Status

The end-to-end location pipeline is operational: Tesla Fleet Telemetry -> VPS receiver -> HTTPS webhook -> Home Assistant `device_tracker`.
