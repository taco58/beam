import socket
import struct
import json

HEADER_FORMAT = "!I"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAX_MESSAGE_SIZE = 10 * 1024 * 1024
CHUNK_SIZE = 64 * 1024

def recv_exact(sock: socket.socket, num_bytes: int) -> bytes:
    chunks = []
    bytes_received = 0

    while bytes_received < num_bytes:
        chunk = sock.recv(num_bytes - bytes_received)

        if not chunk:
            raise ConnectionError("Empty chunk")

        chunks.append(chunk)
        bytes_received += len(chunk)

    return b"".join(chunks)


def send_exact(sock: socket.socket, data: bytes) -> None:
    try:
        sock.sendall(data)
    except OSError:
        raise ConnectionError("Connection lost while sending data")


def send_msg(sock: socket.socket, payload: bytes) -> None:
    header = struct.pack(HEADER_FORMAT, len(payload))
    send_exact(sock, header + payload)


def recv_msg(sock: socket.socket) -> bytes:
    head = recv_exact(sock, HEADER_SIZE)
    length = struct.unpack(HEADER_FORMAT, head)[0]

    if length > MAX_MESSAGE_SIZE:
        raise ValueError("Message length too large")

    msg = recv_exact(sock, length)

    return msg


def send_json(sock: socket.socket, data: dict) -> None:
    payload = json.dumps(data).encode("utf-8")
    send_msg(sock, payload)


def recv_json(sock: socket.socket) -> dict:
    data = recv_msg(sock).decode("utf-8")
    return json.loads(data)



