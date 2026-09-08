from pathlib import Path  
import socket

def get_unique_path(destination_path: Path, filename: str) -> Path:
    dest = destination_path / filename

    file = Path(filename)
    stem = file.stem
    suffix = file.suffix

    count = 1

    while dest.exists():
        new_name = f"{stem} ({count}){suffix}"
        dest = destination_path / new_name
        count += 1

    return dest

def get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"