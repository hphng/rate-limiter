from fastapi import FastAPI

app = FastAPI(title="Rate Limiter API")


@app.get("/")
async def root():
    return {"message": "Rate Limiter API is running"}


@app.get("/health")
async def health():
    return {"status": "ok"}
