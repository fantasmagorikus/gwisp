import io
import ipaddress
import json
import re
import secrets
import socket
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import mss
import requests
from PIL import Image

from gwisp.config import RegionSettings

HOST_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
)
MAX_SYNC_RESPONSE_BYTES = 15 * 1024 * 1024


@dataclass(frozen=True)
class SyncConnectionInfo:
    host: str
    port: int
    token: str

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


def generate_pairing_token() -> str:
    return secrets.token_urlsafe(18)


def format_sync_details(info: SyncConnectionInfo) -> str:
    return "\n".join(
        [
            "Gwisp Sync OCR",
            f"Host: {info.host}",
            f"Port: {info.port}",
            f"Token: {info.token}",
        ]
    )


def parse_sync_details(value: str) -> SyncConnectionInfo:
    fields = _parse_key_value_details(value)
    host = fields.get("host")
    port = fields.get("port")
    token = fields.get("token")

    if not (host and port and token):
        host, port, token = _parse_compact_details(value, host, port, token)

    if not host:
        raise ValueError("Sync OCR details must include host")
    if not port:
        raise ValueError("Sync OCR details must include port")
    if not token:
        raise ValueError("Sync OCR details must include token")

    try:
        parsed_port = int(port)
    except ValueError as exc:
        raise ValueError("Sync OCR port must be a number") from exc
    if parsed_port < 1 or parsed_port > 65535:
        raise ValueError("Sync OCR port must be between 1 and 65535")

    return SyncConnectionInfo(host=_clean_host(host), port=parsed_port, token=token.strip())


def _parse_key_value_details(value: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, raw_field_value = line.split(":", 1)
        normalized_key = key.strip().lower()
        if normalized_key in {"host", "ip", "address", "porta", "port", "token"}:
            field_name = "port" if normalized_key == "porta" else normalized_key
            field_name = "host" if field_name in {"ip", "address"} else field_name
            fields[field_name] = raw_field_value.strip()
    return fields


def _parse_compact_details(
    value: str,
    host: str | None,
    port: str | None,
    token: str | None,
) -> tuple[str | None, str | None, str | None]:
    compact_match = re.search(
        r"(?P<host>[A-Za-z0-9_.-]+):(?P<port>\d{1,5})\s+(?P<token>\S+)",
        value,
    )
    if compact_match:
        host = host or compact_match.group("host")
        port = port or compact_match.group("port")
        token = token or compact_match.group("token")
    return host, port, token


def _clean_host(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith(("http://", "https://")):
        parsed = urlparse(cleaned)
        if parsed.scheme != "http":
            raise ValueError("Sync OCR host must use http:// or a plain host/IP")
        if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
            raise ValueError("Sync OCR host must not include path, query, or fragment")
        cleaned = parsed.hostname or ""
    else:
        cleaned = cleaned.strip("/")

    if not cleaned or any(char in cleaned for char in "/\\:@?#[]"):
        raise ValueError("Sync OCR host must be a plain hostname or IP address")

    try:
        ipaddress.ip_address(cleaned)
        return cleaned
    except ValueError:
        pass

    if not HOST_PATTERN.fullmatch(cleaned):
        raise ValueError("Sync OCR host contains invalid characters")

    return cleaned


def detect_lan_ip() -> str:
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        udp_socket.connect(("8.8.8.8", 80))
        return udp_socket.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        udp_socket.close()


def is_unspecified_host(host: str) -> bool:
    if not host:
        return True
    try:
        return ipaddress.ip_address(host).is_unspecified
    except ValueError:
        return False


def capture_primary_monitor_image() -> Image.Image:
    with mss.MSS() as screen_capture:
        monitor = (
            screen_capture.monitors[1]
            if len(screen_capture.monitors) > 1
            else screen_capture.monitors[0]
        )
        screenshot = screen_capture.grab(monitor)
        return Image.frombytes("RGB", screenshot.size, screenshot.rgb)


class RemoteSyncScreenCapture:
    def __init__(
        self,
        connection_info: SyncConnectionInfo,
        timeout_seconds: float = 5.0,
        max_response_bytes: int = MAX_SYNC_RESPONSE_BYTES,
    ) -> None:
        self.connection_info = connection_info
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes

    def test_connection(self) -> None:
        self._request("/status")

    def capture_region_image(self, _region: RegionSettings) -> Image.Image:
        data = self._request("/capture")
        return Image.open(io.BytesIO(data)).convert("RGB")

    def _request(self, path: str) -> bytes:
        url = f"{self.connection_info.base_url}{path}"
        try:
            response = requests.get(
                url,
                headers={"Authorization": f"Bearer {self.connection_info.token}"},
                timeout=self.timeout_seconds,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Sync OCR connection failed: {exc}") from exc

        if response.is_redirect:
            raise RuntimeError("Sync OCR request refused redirect")
        if response.status_code != HTTPStatus.OK:
            raise RuntimeError(f"Sync OCR request failed with HTTP {response.status_code}")
        if len(response.content) > self.max_response_bytes:
            raise RuntimeError("Sync OCR response was larger than the allowed limit")

        return response.content


class SyncCaptureServer:
    def __init__(
        self,
        host: str | None = None,
        port: int = 0,
        token: str | None = None,
        image_provider: Callable[[], Image.Image] = capture_primary_monitor_image,
    ) -> None:
        self.host = host
        self.port = port
        self.token = token or generate_pairing_token()
        self.image_provider = image_provider
        self.last_client_at: float | None = None
        self._http_server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def connection_info(self) -> SyncConnectionInfo:
        if self._http_server is None:
            raise RuntimeError("Sync OCR server has not started")

        actual_port = self._http_server.server_address[1]
        bound_host = self._http_server.server_address[0]
        display_host = detect_lan_ip() if is_unspecified_host(bound_host) else bound_host
        return SyncConnectionInfo(host=display_host, port=actual_port, token=self.token)

    def start(self) -> None:
        if self._http_server is not None:
            return

        server_owner = self

        class SyncCaptureRequestHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if not self._is_authorized():
                    self.send_error(HTTPStatus.UNAUTHORIZED, "Unauthorized")
                    return

                server_owner.last_client_at = time.monotonic()
                if self.path == "/status":
                    self._send_status()
                    return
                if self.path == "/capture":
                    self._send_capture()
                    return

                self.send_error(HTTPStatus.NOT_FOUND, "Not found")

            def _is_authorized(self) -> bool:
                expected = f"Bearer {server_owner.token}"
                received = self.headers.get("Authorization", "")
                return secrets.compare_digest(received, expected)

            def _send_status(self) -> None:
                payload = json.dumps({"status": "ok"}).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def _send_capture(self) -> None:
                image = server_owner.image_provider().convert("RGB")
                output = io.BytesIO()
                image.save(output, format="PNG")
                payload = output.getvalue()

                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, _format: str, *_args: object) -> None:
                return

        bind_host = self.host or detect_lan_ip()
        if is_unspecified_host(bind_host):
            bind_host = detect_lan_ip()
        self._http_server = ThreadingHTTPServer((bind_host, self.port), SyncCaptureRequestHandler)
        self._thread = threading.Thread(
            target=self._http_server.serve_forever,
            name="Gwisp-SyncOCR-Server",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if self._http_server is None:
            return

        self._http_server.shutdown()
        self._http_server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._http_server = None
        self._thread = None

    def is_connected(self) -> bool:
        return self.last_client_at is not None
