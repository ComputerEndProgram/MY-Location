# Certificate renewal

Caddy renews its own certificate automatically, but Fleet Telemetry and Vehicle Command use locked-down copies of that certificate/key. Those copies must be refreshed after renewal.

The recommended design is:

```text
Caddy certificate directory changes
        -> systemd .path unit
        -> sync-tesla-certs
        -> validate cert/key pair
        -> compare hashes
        -> copy only when changed
        -> restart Tesla containers

plus a daily systemd timer as a fallback.
```

This avoids a long stale-certificate window while retaining a self-healing periodic check.

Install the files in `server/`:

- `sync-tesla-certs`
- `sync-tesla-certs.service`
- `sync-tesla-certs.path`
- `sync-tesla-certs.timer`

Adjust the source certificate directory and deployment paths to the local Caddy installation before enabling them.

The sync script validates that the certificate and private key have the same public key before installing anything. It then compares SHA-256 hashes and exits without restarting services when nothing changed.

Enable the watcher and fallback timer:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sync-tesla-certs.path
sudo systemctl enable --now sync-tesla-certs.timer
```

Verify the path unit is `active (waiting)` and inspect the timer with:

```bash
systemctl status sync-tesla-certs.path
systemctl list-timers sync-tesla-certs.timer
```
