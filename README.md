# Freelance Integration Starter

Tested FastAPI starter for bounded webhook/API integration work. It verifies HMAC signatures, requires idempotency keys, transforms payloads, and exposes a delivery-status log.

## Run

```bash
export WEBHOOK_SECRET=change-me
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

## Endpoints

- `GET /health`
- `POST /webhooks/source`
- `GET /deliveries/{event_id}`

Required webhook headers:

- `X-Signature-SHA256`
- `Idempotency-Key`

## Verify

```bash
.venv/bin/python -m pytest
```

## Production boundary

The in-memory event store is deliberate starter scope. Replace it with PostgreSQL/Redis and add destination delivery with retry/backoff only for a concrete client task.

## License

MIT
