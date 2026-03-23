from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING


def _bootstrap_gcp_credentials() -> None:
    """Support file path, relative path under backend/, or inline JSON (Railway-friendly)."""
    json_inline = (os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON") or "").strip()
    if json_inline:
        try:
            import json
            import tempfile

            json.loads(json_inline)
            fd, tmp_path = tempfile.mkstemp(suffix=".json", text=True)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(json_inline)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp_path
            return
        except Exception:
            pass

    raw = (os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()
    if not raw:
        return
    p = Path(raw)
    if p.is_file():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(p.resolve())
        return
    if not p.is_absolute():
        candidate = Path(__file__).resolve().parent / raw
        if candidate.is_file():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(candidate)


_bootstrap_gcp_credentials()

if TYPE_CHECKING:
    from google.cloud.firestore_v1.async_client import AsyncClient
    from google.cloud.firestore import Client as SyncClient


def _truthy_env(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def firestore_enabled() -> bool:
    """Use Firestore when project id is set and persistence is not disabled."""
    if _truthy_env("FIRESTORE_DISABLED"):
        return False
    project = (os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT") or "").strip()
    if not project:
        project = (os.getenv("FIRESTORE_PROJECT_ID") or "").strip()
    return bool(project)


def firestore_project_id() -> str | None:
    project = (os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT") or "").strip()
    if project:
        return project
    return (os.getenv("FIRESTORE_PROJECT_ID") or "").strip() or None


@lru_cache(maxsize=1)
def get_async_firestore() -> "AsyncClient | None":
    from google.cloud.firestore_v1.async_client import AsyncClient

    if not firestore_enabled():
        return None
    pid = firestore_project_id()
    if not pid:
        return None
    return AsyncClient(project=pid)


@lru_cache(maxsize=1)
def get_sync_firestore() -> "SyncClient | None":
    from google.cloud.firestore import Client as SyncClient

    if not firestore_enabled():
        return None
    pid = firestore_project_id()
    if not pid:
        return None
    return SyncClient(project=pid)


def clear_firestore_caches() -> None:
    get_async_firestore.cache_clear()
    get_sync_firestore.cache_clear()
