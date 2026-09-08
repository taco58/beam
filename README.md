# beam

Zero-config peer-to-peer file transfer CLI for your local network. Like AirDrop, but from your terminal.

## Features

- **Zero-config discovery** — Receiver broadcasts via UDP, sender auto-discovers on Wi-Fi
- **QR code mobile transfer** — Send files to your phone by scanning a QR code
- **Direct IP mode** — Skip discovery and send straight to an IP address
- **Progress bars** — Real-time speed, ETA, and transfer progress via Rich

## Installation

```bash
# Clone and install
git clone https://github.com/taco58/beam.git
cd beam
uv sync
```

## Usage

### Receive a file

Start listening for incoming transfers:

```bash
beam recv
```

Options:
- `--dir, -d <path>` — Save directory (default: current directory)
- `--port, -p <port>` — TCP port to listen on (default: 9876)

### Send a file (peer-to-peer)

Auto-discovers a receiver on your Wi-Fi:

```bash
beam send photo.png
```

Send directly to an IP address:

```bash
beam send photo.png --to 192.168.1.100
```

Options:
- `--to, -t <ip>` — Direct IP address of receiver (skips discovery)
- `--port, -p <port>` — Target port (default: 9876)

### Send a file to your phone (QR code)

Spins up a temporary HTTP server and displays a QR code. Scan it with your phone camera (must be on the same Wi-Fi):

```bash
beam send photo.png --web
```

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest -v
```

## How It Works

1. **Discovery** — Receiver broadcasts UDP beacons (`BEAM_V1`). Sender listens and auto-connects.
2. **Transfer** — Files are streamed over TCP with 4-byte length-prefixed framing, SHA-256 integrity checks, and atomic `.part` file writes.
3. **Web mode** — A temporary threaded HTTP server serves the file. A landing page with a download button avoids mobile browser quirks.
