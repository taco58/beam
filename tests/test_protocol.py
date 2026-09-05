import socket
import pytest
from beam.protocol import (
    send_msg, recv_msg,
    send_json, recv_json,
    recv_exact, MAX_MESSAGE_SIZE, HEADER_FORMAT
)
import struct

@pytest.fixture
def sockets():
    s1, s2 = socket.socketpair()
    yield s1, s2
    s1.close()
    s2.close()

def test_send_and_recv_msg(sockets):
    s1, s2 = sockets
    payload = b"Hello"

    send_msg(s1, payload)
    result = recv_msg(s2)

    assert result == payload

def test_send_and_recv_json(sockets):
    s1, s2 = sockets
    payload = {"msg": "Hello"}

    send_json(s1, payload)
    result = recv_json(s2)

    assert result == payload

def test_oversized_msg(sockets):
    s1, s2 = sockets

    fake_header = struct.pack(HEADER_FORMAT, MAX_MESSAGE_SIZE + 1)

    s1.sendall(fake_header)

    with pytest.raises(ValueError):
        recv_msg(s2)

def test_close_conn(sockets):
    s1, s2 = sockets
    payload = b"Hello"

    s1.sendall(b"abc")
    s1.close()

    with pytest.raises(ConnectionError):
        recv_exact(s2, 10)