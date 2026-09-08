import queue
import socket
import threading
import pytest

from beam.discovery import (
    MAGIC_HEADER,
    broadcast_beacon,
    listen_for_beacons,
)

TEST_PORT = 19875


def test_broadcast_and_listen():
    result_queue = queue.Queue()
    stop_event = threading.Event()

    def run_listener():
        try:
            msg, sender_ip = listen_for_beacons(timeout=3.0, port=TEST_PORT)
            result_queue.put((msg, sender_ip))
        except Exception as err:
            result_queue.put(err)

    listener_thread = threading.Thread(target=run_listener)
    listener_thread.start()

    beacon_info = {
        "filename": "document.pdf",
        "size": 1048576,
        "port": 9876,
    }

    broadcaster_thread = threading.Thread(
        target=broadcast_beacon,
        kwargs={
            "beacon_data": beacon_info,
            "interval": 0.05,
            "stop_event": stop_event,
            "port": TEST_PORT,
        },
    )
    broadcaster_thread.start()

    result = result_queue.get(timeout=4.0)
    stop_event.set()

    listener_thread.join(timeout=2.0)
    broadcaster_thread.join(timeout=2.0)

    assert not isinstance(result, Exception), f"Listener failed with: {result}"
    message, sender_ip = result

    assert message["magic"] == MAGIC_HEADER
    assert message["filename"] == "document.pdf"
    assert message["size"] == 1048576
    assert message["port"] == 9876
    assert isinstance(sender_ip, str)
    assert len(sender_ip) > 0


def test_listen_timeout():
    with pytest.raises((TimeoutError, socket.timeout)):
        listen_for_beacons(timeout=0.2, port=19876)


def test_listener_ignores_unrelated_traffic():
    result_queue = queue.Queue()

    def run_listener():
        msg, _ = listen_for_beacons(timeout=3.0, port=19877)
        result_queue.put(msg)

    listener_thread = threading.Thread(target=run_listener)
    listener_thread.start()

    sender_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sender_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    sender_sock.sendto(b"RANDOM_NETWORK_NOISE_12345", ("255.255.255.255", 19877))

    sender_sock.sendto(b'{"magic": "OTHER_APP", "device": "TV"}', ("255.255.255.255", 19877))

    sender_sock.sendto(
        f'{{"magic": "{MAGIC_HEADER}", "filename": "valid.txt"}}'.encode("utf-8"),
        ("255.255.255.255", 19877),
    )
    sender_sock.close()

    msg = result_queue.get(timeout=3.0)
    listener_thread.join(timeout=2.0)

    assert msg["filename"] == "valid.txt"
