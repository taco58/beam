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

    