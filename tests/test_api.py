import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
SECRET = "test-secret"


def sign(body: bytes) -> str:
    return hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rejects_invalid_signature(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", SECRET)
    response = client.post(
        "/webhooks/source",
        content=b'{"event":"lead.created"}',
        headers={"X-Signature-SHA256": "bad", "Idempotency-Key": "evt-1"},
    )
    assert response.status_code == 401


def test_accepts_valid_event_and_records_delivery(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", SECRET)
    body = json.dumps({"event": "lead.created", "data": {"email": "a@example.com"}}).encode()
    response = client.post(
        "/webhooks/source",
        content=body,
        headers={"X-Signature-SHA256": sign(body), "Idempotency-Key": "evt-2"},
    )
    assert response.status_code == 202
    event_id = response.json()["event_id"]

    status = client.get(f"/deliveries/{event_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "accepted"
    assert status.json()["payload"]["type"] == "lead.created"


def test_duplicate_idempotency_key_returns_same_event(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", SECRET)
    body = json.dumps({"event": "lead.updated", "data": {"id": 7}}).encode()
    headers = {"X-Signature-SHA256": sign(body), "Idempotency-Key": "evt-3"}

    first = client.post("/webhooks/source", content=body, headers=headers)
    second = client.post("/webhooks/source", content=body, headers=headers)

    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["event_id"] == first.json()["event_id"]


def test_requires_idempotency_key(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", SECRET)
    body = b'{"event":"lead.created"}'
    response = client.post(
        "/webhooks/source",
        content=body,
        headers={"X-Signature-SHA256": sign(body)},
    )
    assert response.status_code == 400
