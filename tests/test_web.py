import queue
import threading
import urllib.parse
import urllib.request
from pathlib import Path

from beam.web import serve_file_http


def test_serve_file_http(tmp_path: Path):
    """Verify that an HTTP client can directly download the file."""
    test_file = tmp_path / "photo test.png"
    content = b"PNG_IMAGE_BYTES_12345" * 500
    test_file.write_bytes(content)

    url_queue = queue.Queue()

    def run_server():
        serve_file_http(
            file_path=test_file,
            port=0,
            ready_callback=lambda url: url_queue.put(url),
        )

    server_thread = threading.Thread(target=run_server)
    server_thread.start()

    url = url_queue.get(timeout=5)

    with urllib.request.urlopen(url, timeout=5) as response:
        assert response.status == 200
        assert "text/html" in response.headers.get("Content-Type", "")
        html = response.read().decode("utf-8")
        assert "Tap to Download" in html

    # Download the actual file via /download endpoint
    file_url = url.rstrip("/") + "/download"
    with urllib.request.urlopen(file_url, timeout=5) as response:
        assert response.status == 200
        assert "image/png" in response.headers.get("Content-Type", "")
        assert "attachment" in response.headers.get("Content-Disposition", "")
        downloaded_bytes = response.read()

    server_thread.join(timeout=5)

    assert downloaded_bytes == content