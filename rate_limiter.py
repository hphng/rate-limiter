import json
import time
import asyncio
from pathlib import Path
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

DATA_FILE = Path("data/rate_limit_state.json")
BUCKET_CAPACITY = 10
REFILL_RATE = 1 / 30  # tokens per second (1 token per 30 seconds)

_lock = asyncio.Lock()


def _load_state() -> dict:
    if not DATA_FILE.exists():
        return {}
    try:
        return json.loads(DATA_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(state, indent=2))


def _refill(entry: dict, now: float) -> dict:
    elapsed = now - entry["last_refill"]
    new_tokens = min(BUCKET_CAPACITY, entry["tokens"] + elapsed * REFILL_RATE)
    return {"tokens": new_tokens, "last_refill": now}


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = request.client.host
        allowed = True
        retry_after = 0

        print(f"Processing request from {client_ip} at {time.strftime('%Y-%m-%d %H:%M:%S')}")

        async with _lock:
            state = _load_state()
            now = time.time()

            if client_ip not in state:
                state[client_ip] = {"tokens": float(BUCKET_CAPACITY - 1), "last_refill": now}
                _save_state(state)
            else:
                entry = _refill(state[client_ip], now)
                if entry["tokens"] < 1:
                    allowed = False
                    retry_after = int((1 - entry["tokens"]) / REFILL_RATE)
                    state[client_ip] = entry
                    _save_state(state)
                else:
                    entry["tokens"] -= 1
                    state[client_ip] = entry
                    _save_state(state)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error": "Too many requests"},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
