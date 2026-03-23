import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.session_store import SessionStore
from backend.routers import scrape, session, research, report_card, webhooks, convai

# Always load backend/.env regardless of shell cwd
load_dotenv(Path(__file__).resolve().parent / ".env")

app = FastAPI(title="Donald API")

_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_fe = (os.getenv("FRONTEND_URL") or "").strip()
if _fe:
    _cors_origins.append(_fe)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = SessionStore()
app.state.store = store

app.include_router(scrape.router)
app.include_router(session.router)
app.include_router(research.router)
app.include_router(report_card.router)
app.include_router(webhooks.router)
app.include_router(convai.router)
