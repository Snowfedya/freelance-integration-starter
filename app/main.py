import hashlib
import hmac
import json
import os
import uuid
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, status

app = FastAPI(title="Freelance Integration Starter", version="0.1.0")

events_by_id: dict[str, dict[str, Any]] = {}
event_by_key: dict[str, str] = {}


def valid_signature(body: bytes, signature: str | None) -> bool:
    secret = os.getenv("WEBHOOK_SECRET", "change-me")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return signature is not None and hmac.compare_digest(expected, signature)


def transform(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": payload.get("event", "unknown"),
        "data": payload.get("data", {}),
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/source")
async def receive_webhook(
    request: Request,
    x_signature_sha256: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None),
):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key is required")
    body = await request.body()
    if not valid_signature(body, x_signature_sha256):
        raise HTTPException(status_code=401, detail="Invalid signature")
    if idempotency_key in event_by_key:
        return {"event_id": event_by_key[idempotency_key], "duplicate": True}
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    event_id = str(uuid.uuid4())
    events_by_id[event_id] = {
        "event_id": event_id,
        "idempotency_key": idempotency_key,
        "status": "accepted",
        "payload": transform(payload),
    }
    event_by_key[idempotency_key] = event_id
    return status_response(event_id, status.HTTP_202_ACCEPTED)


def status_response(event_id: str, status_code: int):
    from fastapi.responses import JSONResponse

    return JSONResponse(events_by_id[event_id], status_code=status_code)


@app.get("/deliveries/{event_id}")
def delivery_status(event_id: str):
    event = events_by_id.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
