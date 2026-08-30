# VPS/server setup

The reference deployment is Ubuntu with Docker Compose, Caddy and systemd.

## DNS and firewall

Point a dedicated telemetry hostname at the VPS. Permit inbound TCP 4443 in both the host firewall and cloud-provider firewall. Do **not** expose the Vehicle Command Proxy port.

Caddy should obtain a publicly trusted certificate for the telemetry hostname.

## Fleet Telemetry

Use Tesla's official `tesla/fleet-telemetry` image. Pin a tested image digest in production rather than relying indefinitely on `latest`.

Mount a config and TLS certificate/key into the container and publish:

```yaml
ports:
  - "4443:4443"
```

The receiver config should listen on `0.0.0.0:4443`, enable JSON logging, and route vehicle/connectivity/error records to the logger. See `server/fleet-telemetry-config.example.json`.

The Docker logging driver must send the receiver logs to the local bridge:

```yaml
logging:
  driver: syslog
  options:
    syslog-address: "udp://127.0.0.1:5514"
    syslog-format: "rfc3164"
    tag: "fleet-telemetry"
```

Changing Docker's logging driver requires recreating the container, not merely restarting it.

## Vehicle Command Proxy

Use Tesla's official `tesla/vehicle-command` image and the same virtual-key private key whose public half is enrolled with the vehicle.

Bind the proxy only to localhost:

```yaml
ports:
  - "127.0.0.1:4444:4444"
```

Never open TCP 4444 in the host/cloud firewall.

## Bridge

Install `receiver/bridge.py`, create a random 32-byte webhook secret, configure the same value in MY Location's HA options, and store the resulting webhook URL in a root-readable environment file:

```text
MY_LOCATION_WEBHOOK_URL=https://HA_HOST/api/webhook/RANDOM_SECRET
```

Run the bridge under its own locked-down system account using `server/my-location-bridge.service`.

The bridge listens on `127.0.0.1:5514/UDP`. It ignores non-location records and forwards location as JSON over HTTPS.

## Verification

Useful checks:

```bash
docker compose ps
ss -lntp | grep -E '4443|4444'
ss -lunp | grep 5514
docker inspect fleet-telemetry --format '{{json .HostConfig.LogConfig}}'
journalctl -u my-location-bridge -f
```

Expected network state:

```text
0.0.0.0:4443       public Fleet Telemetry
127.0.0.1:4444     local Vehicle Command Proxy
127.0.0.1:5514/udp local bridge
```

When the vehicle is moving, bridge logs should show `Received telemetry record type=V` followed by `Forwarded location to Home Assistant`.
