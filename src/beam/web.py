import html
import mimetypes
import sys
from http import server
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import quote

import qrcode

from beam.protocol import CHUNK_SIZE
from beam.utils import get_local_ip


def print_terminal_qr(url: str) -> None:
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.print_ascii(invert=True)


class BeamHTTPServer(server.ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        error = sys.exc_info()[1]

        if isinstance(error, (ConnectionResetError, BrokenPipeError)):
            return

        return super().handle_error(request, client_address)


class DownloadHandler(server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def _send_file_headers(self, total_bytes: int, filename: str) -> None:
        content_type, _ = mimetypes.guess_type(filename)

        if not content_type:
            content_type = "application/octet-stream"

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header(
            "Content-Disposition",
            f'attachment; filename="{filename}"'
        )
        self.send_header("Content-Length", str(total_bytes))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

    def do_HEAD(self):
        if self.path != "/download":
            self.send_error(404)
            return

        file_path = self.server.file_path

        try:
            total_bytes = file_path.stat().st_size
        except OSError:
            self.send_error(404)
            return

        self._send_file_headers(total_bytes, file_path.name)

    def _serve_landing_page(self):
        file_path = self.server.file_path
        display_name = html.escape(file_path.name)

        html_content = f"""<!DOCTYPE html>
                            <html>
                            <head>
                                <meta name="viewport" content="width=device-width, initial-scale=1">
                                <title>beam</title>
                                <style>
                                    body {{
                                        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                                        display: flex;
                                        justify-content: center;
                                        align-items: center;
                                        min-height: 100vh;
                                        margin: 0;
                                        background: #111;
                                        color: #fff;
                                    }}

                                    .card {{
                                        text-align: center;
                                        padding: 2rem;
                                        max-width: 90%;
                                    }}

                                    .filename {{
                                        font-size: 1.2rem;
                                        margin-bottom: 1.5rem;
                                        word-break: break-all;
                                    }}

                                    a {{
                                        display: inline-block;
                                        padding: 1rem 2rem;
                                        background: #4CAF50;
                                        color: #fff;
                                        text-decoration: none;
                                        border-radius: 8px;
                                        font-size: 1.1rem;
                                    }}
                                </style>
                            </head>
                            <body>
                                <div class="card">
                                    <div class="filename">{display_name}</div>
                                    <a href="/download">Tap to Download</a>
                                </div>
                            </body>
                            </html>
                            """

        data = html_content.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            self._serve_landing_page()
            return

        if self.path != "/download":
            self.send_error(404)
            return

        file_path = self.server.file_path

        try:
            total_bytes = file_path.stat().st_size
        except OSError:
            self.send_error(404)
            return

        self._send_file_headers(total_bytes, file_path.name)

        bytes_sent = 0

        try:
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)

                    if not chunk:
                        self.server.download_completed = True
                        break

                    self.wfile.write(chunk)
                    bytes_sent += len(chunk)

                    callback = self.server.progress_callback
                    if callback:
                        callback(bytes_sent, total_bytes)

        except (BrokenPipeError, ConnectionResetError):
            pass


def serve_file_http(
    file_path: Path,
    port: int = 0,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    ready_callback: Optional[Callable[[str], None]] = None,
) -> str:

    file_path = Path(file_path).resolve()

    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    local_ip = get_local_ip()

    httpd = BeamHTTPServer(
        ("0.0.0.0", port),
        DownloadHandler,
    )

    httpd.file_path = file_path
    httpd.timeout = 0.5
    httpd.progress_callback = progress_callback
    httpd.download_completed = False

    assigned_port = httpd.server_port

    download_url = f"http://{local_ip}:{assigned_port}/"

    if ready_callback:
        ready_callback(download_url)

    print(f"Serving: {file_path}")
    print(f"Open on your phone: {download_url}")

    print_terminal_qr(download_url)

    try:
        while not httpd.download_completed:
            httpd.handle_request()
    finally:
        httpd.server_close()

    return download_url