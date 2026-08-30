# Home Assistant setup

## Installation

Install MY Location through HACS as a custom integration, restart Home Assistant, add Tesla application credentials, then add the MY Location integration and complete Tesla OAuth.

## Bridge secret

Generate a long random value on the VPS, for example:

```bash
openssl rand -hex 32
```

Do not commit or share this value. Configure it in the MY Location integration options and use the same value as the webhook path on the bridge:

```text
https://HA_HOST/api/webhook/SECRET
```

## Configure telemetry

After the public receiver and Vehicle Command Proxy are ready, use the integration's **Configure telemetry** action/button. The integration uses its stored Tesla OAuth token to request the Fleet Telemetry configuration; the private virtual key remains on the VPS.

## Device tracker

After the first successfully forwarded location, the integration exposes a GPS `device_tracker`. Home Assistant resolves its coordinates against configured zones, so its state can become `home`, `not_home`, or another zone.

The default entity ID may be generic. It is safe to rename the entity ID in Home Assistant (for example `device_tracker.tesla_location`) before referencing it in automations.

## Garage automation guidance

Use normal Home Assistant zone/state transitions. Before replacing an existing tracker, verify MY Location over at least one real departure and arrival. For a physical garage door, retain suitable safety conditions and avoid triggering solely from stale or unavailable tracker data.
