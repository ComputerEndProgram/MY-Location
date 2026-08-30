#!/usr/bin/env python3
"""Forward only Tesla Fleet Telemetry Location records to Home Assistant."""

from __future__ import annotations

import json
import os
import socket
import sys
import urllib.error
import urllib.request

LISTEN_HOST = os.environ.get("MY_LOCATION_LISTEN_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("MY_LOCATION_LISTEN_PORT", "5514"))
WEBHOOK_URL = os.environ["MY_LOCATION_WEBHOOK_URL"]


def forward_location(payload: dict) -> None:
    """Forward a single Location record to Home Assistant."""
    if payload.get("msg") != "record_payload":
        return

    data = payload.get("data")
    if not isinstance(data, dict):
        return

    location = data.get("Location")
    if not isinstance(location, dict):
        return

    latitude = location.get("latitude")
    longitude = location.get("longitude")
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        return

    vin = data.get("Vin")
    body = {
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": data.get("CreatedAt"),
    }
    if isinstance(vin, str) and len(vin) >= 4:
        body["vin_last_4"] = vin[-4:]

    request = urllib.request.Request(
        WEBHOOK_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status >= 300:
                print(f"Home Assistant returned HTTP {response.status}", file=sys.stderr)
    except (urllib.error.URLError, TimeoutError) as err:
        print(f"Unable to forward location: {err}", file=sys.stderr)


def main() -> None:
    """Listen for Docker syslog datagrams."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_HOST, LISTEN_PORT))
    print(f"MY Location bridge listening on {LISTEN_HOST}:{LISTEN_PORT}", flush=True)

    while True:
        packet, _ = sock.recvfrom(65535)
        text = packet.decode("utf-8", errors="replace")
        start = text.find("{")
        if start == -1:
            continue
        try:
            payload = json.loads(text[start:])
        except json.JSONDecodeError:
            continue
        forward_location(payload)


if __name__ == "__main__":
    main()
