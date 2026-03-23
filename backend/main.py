import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from backend.logging_config import configure_logging
from backend.middleware.activity_tracker import ActivityTrackerMiddleware
from backend.middleware.rate_limiter import RateLimitMiddleware
from backend.middleware.security import (
    MaxBodySizeMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from backend.session_store import SessionStore
from backend.telemetry import init_telemetry
from backend.routers import scrape, session, research, report_card, webhooks, convai

# Always load backend/.env regardless of shell cwd
load_dotenv(Path(__file__).resolve().parent / ".env")

configure_logging()
init_telemetry()

if (os.getenv("SENTRY_DSN") or "").strip():
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        environment=(os.getenv("ENVIRONMENT") or "development").strip(),
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=float((os.getenv("SENTRY_TRACES_SAMPLE_RATE") or "0.1").strip()),
    )

app = FastAPI(title="Donald API")

_trusted = (os.getenv("TRUSTED_HOSTS") or "").strip()
if _trusted:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[h.strip() for h in _trusted.split(",") if h.strip()],
    )

_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_fe = (os.getenv("FRONTEND_URL") or "").strip()
if _fe:
    _cors_origins.append(_fe)

# First added = outermost (runs first on incoming request)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(MaxBodySizeMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ActivityTrackerMiddleware)

store = SessionStore()
app.state.store = store

app.include_router(scrape.router)
app.include_router(session.router)
app.include_router(research.router)
app.include_router(report_card.router)
app.include_router(webhooks.router)
app.include_router(convai.router)

if not (os.getenv("OTEL_SDK_DISABLED") or "").strip().lower() in ("1", "true", "yes") and (
    os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or ""
).strip():
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception:
        pass


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    from backend.database import firestore_enabled, get_async_firestore
    from backend.redis_client import get_async_redis, redis_enabled

    checks: dict = {}
    ok = True

    if redis_enabled():
        try:
            r = await get_async_redis()
            if r:
                await r.ping()
                checks["redis"] = "ok"
            else:
                checks["redis"] = "disabled"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"
            ok = False
    else:
        checks["redis"] = "disabled"

    if firestore_enabled():
        db = get_async_firestore()
        if db:
            try:
                async for _ in db.collection("sessions").limit(1).stream():
                    break
                checks["firestore"] = "ok"
            except Exception as exc:
                checks["firestore"] = f"error: {exc}"
                ok = False
        else:
            checks["firestore"] = "no_client"
            ok = False
    else:
        checks["firestore"] = "disabled"

    return JSONResponse(
        status_code=200 if ok else 503,
        content={"ready": ok, "checks": checks},
    )
