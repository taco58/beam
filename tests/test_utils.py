from pathlib import Path
import queue
import threading                                                                                                                          
from beam.tcp import recv_file, send_file
from beam.utils import get_unique_path


def test_get_unique_path_no_collision(tmp_path: Path):
    result = get_unique_path(tmp_path, "document.pdf")
    assert result == tmp_path / "document.pdf"


def test_get_unique_path_with_collisions(tmp_path: Path):
    file1 = tmp_path / "photo.jpg"
    file1.write_text("first photo")

    result1 = get_unique_path(tmp_path, "photo.jpg")
    assert result1 == tmp_path / "photo (1).jpg"

    file2 = tmp_path / "photo (1).jpg"
    file2.write_text("second photo")

    result2 = get_unique_path(tmp_path, "photo.jpg")
    assert result2 == tmp_path / "photo (2).jpg"


def test_get_unique_path_no_extension(tmp_path: Path):
    file1 = tmp_path / "Dockerfile"
    file1.write_text("FROM python:3.11")

    result = get_unique_path(tmp_path, "Dockerfile")
    assert result == tmp_path / "Dockerfile (1)"

def test_transfer_collision_avoidance(tmp_path):                                                                                                                                                              
    sender_dir = tmp_path / "sender"                                                                                                              
    receiver_dir = tmp_path / "receiver"                                                                                                          
    sender_dir.mkdir()                                                                                                                            
    receiver_dir.mkdir()

    existing_file = receiver_dir / "report.pdf"
    existing_file.write_bytes(b"Original existing file")

    sender_file = sender_dir / "report.pdf"
    new_content = b"Brand new incoming file"
    sender_file.write_bytes(new_content)

    port_queue = queue.Queue()

    def run_receiver():
        recv_file(
            save_dir=receiver_dir,
            port=0,
            port_callback=lambda p: port_queue.put(p),
        )

    receiver_thread = threading.Thread(target=run_receiver)
    receiver_thread.start()

    port = port_queue.get(timeout=5)
    send_file("127.0.0.1", port, sender_file)
    receiver_thread.join(timeout=5)

    assert existing_file.read_bytes() == b"Original existing file"
    
    renamed_file = receiver_dir / "report (1).pdf"
    assert renamed_file.is_file()
    assert renamed_file.read_bytes() == new_content