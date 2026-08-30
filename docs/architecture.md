# Architecture and security

## Components

1. **Home Assistant custom integration** — owns Tesla OAuth, registers the webhook, exposes the location `device_tracker`, and provides the Configure telemetry action.
2. **Tesla Fleet Telemetry receiver** — official `tesla/fleet-telemetry` container, publicly reachable over TLS/mTLS.
3. **Tesla Vehicle Command Proxy** — official `tesla/vehicle-command` container used to sign telemetry configuration. It must remain localhost-only.
4. **MY Location bridge** — `receiver/bridge.py`; receives the Fleet Telemetry container's JSON logs over localhost UDP, extracts only `Location`, and POSTs it to HA.
5. **Caddy** — obtains public TLS certificates and can expose only the narrow telemetry-configuration route required by Home Assistant.

## Network boundaries

Recommended listeners:

| Listener | Exposure | Purpose |
|---|---|---|
| TCP 443 | Public | Caddy / normal HTTPS |
| TCP 4443 | Public | Tesla Fleet Telemetry mTLS receiver |
| TCP 4444 | `127.0.0.1` only | Tesla Vehicle Command Proxy |
| UDP 5514 | `127.0.0.1` only | Fleet Telemetry JSON log bridge |

Do not expose 4444 or 5514 publicly.

## Data flow

```text
Vehicle -> :4443 fleet-telemetry -> localhost syslog -> bridge
       -> HTTPS webhook -> Home Assistant -> device_tracker
```

Only latitude, longitude, Tesla telemetry timestamp, and optionally the final four VIN characters are forwarded by the bridge. The bridge does not intentionally log coordinates or full VINs.

## Secret inventory

Secrets that belong outside Git:

- Tesla OAuth client secret
- Tesla OAuth access/refresh tokens
- random HA webhook ID/secret
- Tesla virtual-key private key
- TLS private keys

The Tesla virtual-key public key is intentionally public and is served from the partner domain at Tesla's required well-known path during partner setup.

## Failure model

If the VPS or HA is unavailable, location updates are temporarily lost; this is a live tracker rather than a durable telemetry database. HA retains its last tracker state across ordinary integration reloads/restarts. Automations should therefore be designed around HA zone transitions and should include whatever safety conditions are appropriate for the physical garage-door installation.
