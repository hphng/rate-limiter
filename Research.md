# Rate Limiter for FastAPI

## Important
- This file is research for everything needed to build a backend server with a rate limiter.
- The basic tech stack should be FastAPI as a backend server.
- Everything here is not a source of truth — it might be wrong or have tradeoffs. For Claude: if you want to suggest by adding/changing something, please justify your reason with tradeoffs (pros and cons).


## Rate Limiter Algorithms

Before picking an implementation, here are the main algorithms. Each handles the burst/sustained-rate tradeoff differently.

### Fixed Window Counter
- Divide time into fixed buckets (e.g., 00:00–01:00, 01:00–02:00). Count requests per bucket.
- **Pros:** Simplest to implement; O(1) memory per user.
- **Cons:** "Edge burst" problem — a user can send 2× the limit by hitting the tail of one window and the head of the next.

### Sliding Window Log
- Store a timestamp for every request in a sorted list. On each request, drop old timestamps outside the window and count remaining.
- **Pros:** Perfectly accurate; no edge burst.
- **Cons:** Memory grows with request count (O(N) per user); expensive to query.

### Sliding Window Counter (Hybrid)
- Blend two fixed windows using a weighted average to approximate a sliding window.
- **Pros:** Near-accurate with O(1) memory.
- **Cons:** Approximation, not exact; slightly complex math.

### Token Bucket ← chosen approach
- A bucket holds up to `capacity` tokens. Tokens refill at a fixed rate. Each request consumes 1 token. If the bucket is empty, the request is rejected.
- **Pros:** Allows controlled bursting (up to `capacity`); smooth sustained rate; easy to reason about.
- **Cons:** Two parameters to tune (`capacity` + `refill_rate`); a large capacity can allow large bursts.

> **Correction on the original token bucket config:**
> The original doc said "fill 1 request per 10 seconds" for a "10 req / 5 min" limit.
> 1 token / 10 s = 6 tokens / min ≠ 2 tokens / min (10 / 5 min).
> The correct values for the stated limit are:
>
> | Testing target   | Bucket capacity | Refill rate            |
> |------------------|-----------------|------------------------|
> | 10 req / 5 min   | 10 tokens       | 1 token / 30 seconds   |
> | 100 req / min    | 100 tokens      | ~1.67 tokens / second  |
> | 1 000 req / hour | 200 tokens      | ~0.28 tokens / second  |
>
> Capacity controls the burst; refill rate controls the sustained throughput.
> For testing, a capacity of 10 and a 30-second refill interval is the correct mapping.

### Leaky Bucket
- Requests enter a queue; they are processed at a constant output rate. Overflow is dropped.
- **Pros:** Perfectly smooth output; protects downstream.
- **Cons:** Doesn't allow any bursting; adds latency (queue drain); more complex.


## Storage Options

### 1. In-Process Memory (Middleware Cache)
Store the per-IP bucket state in a Python `dict` inside the FastAPI process.

```python
# state lives here
buckets: dict[str, {"tokens": float, "last_refill": float}] = {}
```

- **Pros:** Zero dependencies; instant reads/writes; no network overhead.
- **Cons:** State is lost on restart; does **not** work across multiple workers/replicas (each process has its own dict — limits are per-worker, not global); concurrency risk with async code if not handled carefully.
- **Verdict:** Fine for local prototyping with a single worker (`uvicorn --workers 1`). Not for production.

### 2. File-Based Storage (`/data` folder) ← chosen for prototype
Store bucket state as a JSON file, one entry per IP.

```
/data/rate_limit_state.json
{ "127.0.0.1": { "tokens": 8.0, "last_refill": 1714000000.0 }, ... }
```

- **Pros:** State survives restarts; no extra services; easy to inspect/debug; zero infrastructure.
- **Cons:** Disk I/O on every request (slow under load); file locking needed to prevent race conditions under concurrency; not suitable beyond a single instance; manual cleanup of stale entries required.
- **Verdict:** Good for a prototype with low traffic. Use `fcntl` (Unix) or `msvcrt` (Windows) for file locking, or serialize access with `asyncio.Lock`.

> **Recommended for this prototype:** use file-based storage with a single `asyncio.Lock` so concurrent requests don't corrupt the file.

### 3. Redis
Store bucket state in Redis using atomic operations (e.g., `SET`, `INCR`, Lua scripts, or Redis modules).

- **Pros:** Fast (in-memory); atomic ops prevent race conditions; survives restarts; works across multiple workers and replicas; TTL support for automatic expiry.
- **Cons:** Requires a running Redis instance; adds a network hop per request; operational overhead; overkill for a prototype.
- **Verdict:** The right choice for production. Use `redis-py` (sync) or `aioredis` / `redis.asyncio` (async). See `fastapi-limiter` dependency below.


## Implementation Approach (Prototype)

```
FastAPI app
  └── Middleware (runs on every request)
        ├── Extract client IP from request
        ├── Load /data/rate_limit_state.json (with asyncio.Lock)
        ├── Run token bucket refill logic
        ├── If tokens >= 1: consume token, save state, allow request
        └── If tokens == 0: return HTTP 429 Too Many Requests
```

Key details:
- Use `starlette.middleware.base.BaseHTTPMiddleware` for the middleware.
- Return a `Retry-After` header so clients know when to retry.
- Store `last_refill` as a Unix timestamp float.
- Token refill formula: `new_tokens = min(capacity, stored_tokens + (now - last_refill) * refill_rate)`

**Pros of middleware approach:** Applies to all routes automatically; no per-route decoration needed.
**Cons of middleware approach:** Harder to apply different limits per route; runs even on routes that don't need it (e.g., `/health`).

**Alternative — FastAPI `Depends`:** inject a rate-limit check as a dependency on specific routes.
- **Pros:** Per-route granularity; easy to skip on health/metrics endpoints.
- **Cons:** Must be added to every route manually; easy to forget.


## Dependencies

### `slowapi` ← recommended for prototype if using a library
Thin wrapper around the `limits` library, designed to mirror Flask-Limiter's API.

```bash
pip install slowapi
```

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/items")
@limiter.limit("10/5minutes")
async def items(request: Request): ...
```

- **Pros:** Minimal boilerplate; human-readable limit strings (`"10/5minutes"`); supports in-memory and Redis backends; actively maintained.
- **Cons:** Adds a dependency; the in-memory backend has the same multi-worker problem as option 1; limit string syntax hides the underlying algorithm (fixed window by default, not token bucket).

### `fastapi-limiter`
Redis-native rate limiter for FastAPI using `Depends`.

```bash
pip install fastapi-limiter
```

- **Pros:** Production-ready; Redis backend; uses FastAPI's dependency injection cleanly.
- **Cons:** Requires Redis even for local dev; less flexible algorithm support.

### `limits`
The underlying library used by `slowapi`. Can be used directly for full control.

- **Pros:** Supports multiple storage backends (memory, Redis, Memcached, MongoDB); multiple algorithms.
- **Cons:** More manual wiring; lower-level API.

### Manual implementation ← chosen for prototype
Write the token bucket logic yourself (no extra library).

- **Pros:** Full control over the algorithm; no dependency risk; teaches the mechanics; easy to adapt.
- **Cons:** More code to maintain; edge cases to handle (clock skew, file corruption, concurrent writes).


## Decision Summary

| Concern          | Prototype choice            | Production upgrade path          |
|------------------|-----------------------------|----------------------------------|
| Algorithm        | Token Bucket (manual)       | Same, or use `limits` library    |
| Storage          | File (`/data/`)             | Redis with `redis.asyncio`       |
| Integration      | Middleware                  | Middleware or `Depends` per route|
| Library          | None (manual)               | `slowapi` or `fastapi-limiter`   |
| Workers          | Single (`--workers 1`)      | Multiple, with Redis             |