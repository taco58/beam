import socket
import threading
import time
import json
from typing import Optional

DISCOVERY_PORT = 9875
BROADCAST_ADDR = "255.255.255.255"
MAGIC_HEADER = "BEAM_V1"


def broadcast_beacon(beacon_data: dict, interval: float = 1.0, stop_event: Optional[threading.Event] = None, port: int = DISCOVERY_PORT) -> None:
    beacon_data = {"magic": MAGIC_HEADER, **beacon_data}
    payload = json.dumps(beacon_data).encode("utf-8")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        while True:
            sock.sendto(payload, (BROADCAST_ADDR, port))

            if stop_event:
                if stop_event.wait(interval):
                    break
            else:
                time.sleep(interval)


def listen_for_beacons(timeout: Optional[float] = None, port: int = DISCOVERY_PORT) -> tuple[dict, str]:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", port))

        if timeout:
            sock.settimeout(timeout)

        while True:
            try:
                data, (sender_ip, _) = sock.recvfrom(4096)
                message = json.loads(data.decode("utf-8"))
                if message.get("magic") == MAGIC_HEADER:
                    return (message, sender_ip)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass