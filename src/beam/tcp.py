import socket
import hashlib
from pathlib import Path
from typing import Callable, Optional, Tuple, Dict, Any

from beam.protocol import (
    CHUNK_SIZE, 
    recv_exact,
    recv_json,
    send_json,
    send_exact
)


def hash_file(file_path: Path) -> Tuple[int, str]:
    hasher = hashlib.sha256()
    total_bytes = 0

    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)

            if chunk == b"":
                break

            hasher.update(chunk)
            total_bytes += len(chunk)

    return (total_bytes, hasher.hexdigest())


def send_file(host: str, port: int, file_path: Path, progress_callback: Optional[Callable[[int, int], None]] = None):
    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError("File path did not lead to valid file")

    (file_size, sha256) = hash_file(file_path)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))

        metadata = {
            "filename": file_path.name,
            "size": file_size,
            "sha256": sha256
        }

        send_json(sock, metadata)

        response = recv_json(sock)

        if not response.get("accepted"):
            raise PermissionError("Transfer rejected by receiver")

        bytes_sent = 0

        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)

                if chunk == b"":
                    break

                send_exact(sock, chunk)
                bytes_sent += len(chunk)

                if progress_callback:
                    progress_callback(bytes_sent, file_size)


def recv_file(save_dir: Path, port: int = 0, confirm_callback: Optional[Callable[[Dict[str, Any]], bool]] = None, progress_callback: Optional[Callable[[int, int], None]] = None, port_callback: Optional[Callable[[int], None]] = None) -> Path:
    save_dir = Path(save_dir)
    save_dir.mkdir(parents = True, exist_ok=True)
    hasher = hashlib.sha256()

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("0.0.0.0", port))

    assigned_port = server_sock.getsockname()[1]
    if port_callback:
        port_callback(assigned_port)

    server_sock.listen(1)

    client_sock, client_addr = server_sock.accept()

    try:
        metadata = recv_json(client_sock)

        safe_filename = Path(metadata["filename"]).name
        save_path = save_dir / safe_filename

        accepted = True

        if confirm_callback:
            accepted = confirm_callback(metadata)

        if not accepted:
            send_json(client_sock, {"accepted": False, "reason": "Declined by user"})
            raise PermissionError("Transfer declined")

        send_json(client_sock, {"accepted": True})

        with open(save_path, "wb") as f:
            bytes_received = 0

            while bytes_received != metadata["size"]:
                to_read = min(CHUNK_SIZE, metadata["size"] - bytes_received)
                chunk = recv_exact(client_sock, to_read)
                f.write(chunk)
                hasher.update(chunk)
                bytes_received += len(chunk)

                if progress_callback:
                    progress_callback(bytes_received, metadata["size"])

            if not hasher.hexdigest() == metadata["sha256"]:
                save_path.unlink()
                raise ValueError("SHA-256 mismatch: file corrupted")
    finally:
        server_sock.close()
        client_sock.close()

    return save_path

