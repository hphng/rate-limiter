# Rate Limiter — Implementation Plan

## Context
Building a FastAPI backend prototype with a manual token bucket rate limiter stored in a local JSON file. No external dependencies beyond FastAPI and uvicorn. Single worker only (file-based storage requires it). Limits: 10 tokens capacity, 1 token refilled every 30 seconds, applied per client IP.

---

## Project Structure (final)
```
rate limiter/
├── main.py               # FastAPI app + middleware wiring
├── rate_limiter.py       # Token bucket logic + file I/O
├── data/                 # gitignored — created at runtime
├── .gitignore
├── requirements.txt
└── Research.md
```

---

## Phase 1 — FastAPI Boilerplate

### Files to create

**`.gitignore`**
```
data/
__pycache__/
*.pyc
.env
.venv
```

**`requirements.txt`**
```
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
```

**`main.py`**
```python
from fastapi import FastAPI

app = FastAPI(title="Rate Limiter API")

@app.get("/")
async def root():
    return {"message": "Rate Limiter API is running"}

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### Verification
1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the server:
   ```bash
   uvicorn main:app --reload --workers 1
   ```
4. `GET /` → `{"message": "Rate Limiter API is running"}`
5. `GET /health` → `{"status": "ok"}`

---

## Phase 2 — Token Bucket Middleware

### Config (from Research.md)
| Parameter       | Value                        |
|-----------------|------------------------------|
| Bucket capacity | 10 tokens                    |
| Refill rate     | 1 token / 30 seconds         |
| State file      | `data/rate_limit_state.json` |
| Key             | Client IP address            |
| Skip path       | `/health`                    |

### New file: `rate_limiter.py`

Responsibilities:
- Load/save JSON state from `data/rate_limit_state.json`
- `_refill(entry, now)` — apply elapsed-time token refill, clamp to capacity
- `RateLimiterMiddleware` — `BaseHTTPMiddleware` subclass:
  1. Skip `/health` entirely
  2. Acquire `asyncio.Lock` (prevents concurrent file corruption)
  3. Load state, create entry if new IP (consume 1 token immediately)
  4. Refill existing entry, check `tokens >= 1`
  5. If empty → return `JSONResponse(429)` with `Retry-After` header; **release lock before returning**
  6. Decrement token, save state, release lock
  7. Call `call_next(request)` **outside** the lock (don't hold lock during handler execution)

Token refill formula:
```python
elapsed = now - entry["last_refill"]
new_tokens = min(BUCKET_CAPACITY, entry["tokens"] + elapsed * REFILL_RATE)
```

`Retry-After` calculation:
```python
retry_after = int((1 - entry["tokens"]) / REFILL_RATE)
```

### Modified file: `main.py`
Add two lines to wire the middleware after the app is created:
```python
from rate_limiter import RateLimiterMiddleware
app.add_middleware(RateLimiterMiddleware)
```

### Runtime directory creation
The `data/` folder is gitignored. The middleware creates it automatically on first write:
```python
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
```
No manual setup needed.

### Verification
1. Start server: `uvicorn main:app --reload --workers 1`
2. Send 10 rapid requests to `GET /` → all return 200
3. Send 11th request → `HTTP 429` with `{"error": "Too Many Requests"}` and `Retry-After` header
4. `GET /health` → always returns 200 (exempt from rate limiting)
5. Inspect `data/rate_limit_state.json` to confirm token count decremented correctly
