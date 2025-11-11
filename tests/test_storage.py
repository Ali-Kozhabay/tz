from datetime import UTC, datetime, timedelta

from app.schemas import StorageSignRequest
from app.services.storage import StorageService


def test_signed_url_ttl_close_to_five_minutes():
    service = StorageService()
    result = service.sign(StorageSignRequest(key="videos/sample.mp4", method="get"))
    assert result.url.startswith("http")
    expires_in = result.expires_at - datetime.now(UTC)
    assert timedelta(minutes=4, seconds=50) <= expires_in <= timedelta(minutes=5, seconds=5)
