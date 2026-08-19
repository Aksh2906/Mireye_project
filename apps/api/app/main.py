from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.middleware import ApiKeyMiddleware, RateLimitMiddleware, RequestContextMiddleware

settings = get_settings()
app = FastAPI(title="Mireye Agricultural Acquisition Intelligence", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[value.strip() for value in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ApiKeyMiddleware)
app.add_middleware(RequestContextMiddleware)
app.include_router(api_router, prefix="/api")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
