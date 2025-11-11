from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_db_session
from app.api.routes.chat import router as chat_router


class _StubResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _StubSession:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, statement):  # noqa: ARG002 - statement unused in stub
        return _StubResult(self._rows)


def _build_client(rows):
    app = FastAPI()
    app.include_router(chat_router)

    async def override_session():
        yield _StubSession(rows)

    app.dependency_overrides[get_db_session] = override_session
    return TestClient(app)


def test_chat_docs_endpoint_describes_websocket():
    rows = [("general", False)]
    with _build_client(rows) as client:
        response = client.get("/chat/docs")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ws_url"] == "/ws/channels/{slug}"
    assert "Authorization" in payload["auth"]
    assert "message.create" in payload["events"]
    assert "message.history" in payload["broadcasts"]


def test_list_channels_returns_stubbed_rows():
    rows = [("general", False), ("announcements", True)]
    with _build_client(rows) as client:
        response = client.get("/chat/channels")
    assert response.status_code == 200
    assert response.json() == [
        {"slug": "general", "is_readonly": False},
        {"slug": "announcements", "is_readonly": True},
    ]
