from pathlib import Path  


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