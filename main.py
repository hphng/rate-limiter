from fastapi import FastAPI
from rate_limiter import RateLimiterMiddleware

app = FastAPI(title="Rate Limiter API")
app.add_middleware(RateLimiterMiddleware)


@app.get("/")
async def root():
    return {"message": "Rate Limiter API is running"}


@app.get("/health")
async def health():
    return {"status": "ok"}
