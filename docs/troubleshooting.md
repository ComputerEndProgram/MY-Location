# Troubleshooting

## Fleet Telemetry container restarts / permission denied

Tesla's images may run as an unprivileged numeric UID. Ensure the mounted TLS certificate/key are readable by the container user without making the private key world-readable.

## `curl` to :4443 says `certificate required`

This is expected for the Fleet Telemetry receiver: it requires the vehicle's client certificate/mTLS. A successful TLS handshake followed by a client-certificate-required alert is evidence that the listener is alive.

## Vehicle Command Proxy returns 403 without token

A response such as `client did not provide an OAuth token` is expected when testing the proxy without an Authorization header. Keep the proxy localhost-only.

## Bridge only shows connectivity

Connectivity records prove the car can connect. `V` records containing `Location` are emitted according to the configured location policy. If `minimum_delta` is set, a stationary vehicle may not send another location until it moves sufficiently.

## Bridge receives nothing

Check Docker's active logging driver:

```bash
docker inspect fleet-telemetry --format '{{json .HostConfig.LogConfig}}'
```

It should be `syslog` with `udp://127.0.0.1:5514`. If it is still `json-file`, ensure the `logging:` block is under the **fleet-telemetry** service and recreate the container:

```bash
docker compose up -d --force-recreate fleet-telemetry
```

## `Home Assistant returned HTTP 403`

Test the exact webhook URL from the VPS without printing the secret. If a curl POST succeeds but Python fails, compare request headers/user-agent. The current bridge sets an explicit user agent and JSON accept/content headers because this resolved a real 403 encountered through the production HTTP path.

## Tracker remains `unknown`

The tracker remains unknown until its first valid webhook location arrives. Watch:

```bash
journalctl -u my-location-bridge -f
```

A healthy moving-vehicle path shows:

```text
Received telemetry record type=V
Forwarded location to Home Assistant
```

Then inspect the tracker in Home Assistant Developer Tools -> States for latitude, longitude and the telemetry timestamp.
