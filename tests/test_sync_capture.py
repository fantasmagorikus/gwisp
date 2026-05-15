import pytest
from PIL import Image

from gwisp.adapters.sync_capture import (
    RemoteSyncScreenCapture,
    SyncCaptureServer,
    SyncConnectionInfo,
    format_sync_details,
    parse_sync_details,
)
from gwisp.config import RegionSettings


def test_sync_details_round_trip_from_secondary_to_primary() -> None:
    info = SyncConnectionInfo(host="192.0.2.44", port=49152, token="abc-123")

    pasted_details = format_sync_details(info)
    parsed = parse_sync_details(pasted_details)

    assert parsed == info


def test_parse_sync_details_rejects_missing_token() -> None:
    with pytest.raises(ValueError, match="token"):
        parse_sync_details("Host: 192.0.2.44\nPort: 49152")


def test_parse_sync_details_rejects_host_with_path() -> None:
    with pytest.raises(ValueError, match="path"):
        parse_sync_details("Host: http://192.0.2.44/capture\nPort: 49152\nToken: abc-123")


def test_remote_sync_client_fetches_png_capture_with_token() -> None:
    image = Image.new("RGB", (12, 8), "white")
    server = SyncCaptureServer(
        host="127.0.0.1",
        port=0,
        token="test-token",
        image_provider=lambda: image,
    )
    server.start()

    try:
        client = RemoteSyncScreenCapture(server.connection_info, timeout_seconds=2)
        client.test_connection()
        captured = client.capture_region_image(RegionSettings())

        assert captured.size == (12, 8)
        assert server.is_connected()
    finally:
        server.stop()


def test_remote_sync_client_rejects_wrong_token() -> None:
    server = SyncCaptureServer(
        host="127.0.0.1",
        port=0,
        token="right-token",
        image_provider=lambda: Image.new("RGB", (1, 1), "white"),
    )
    server.start()

    try:
        wrong_info = SyncConnectionInfo(
            host=server.connection_info.host,
            port=server.connection_info.port,
            token="wrong-token",
        )
        client = RemoteSyncScreenCapture(wrong_info, timeout_seconds=2)

        with pytest.raises(RuntimeError, match="401"):
            client.test_connection()
    finally:
        server.stop()
