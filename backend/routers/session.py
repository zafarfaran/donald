from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from backend.models import UserProfile
from backend.session_id import ensure_session_id

router = APIRouter()


class SessionRequest(BaseModel):
    name: str
    degree: str
    university: str
    graduation_year: int
    current_job: str
    current_company: str = ""
    salary: int | None = None
    years_experience: int | None = None
    source: str = "manual"


class SessionResponse(BaseModel):
    session_id: str


@router.post("/api/session", response_model=SessionResponse)
async def create_session(req: SessionRequest, request: Request):
    profile = UserProfile(**req.model_dump())
    session_id = await request.app.state.store.create(profile)
    return SessionResponse(session_id=session_id)


@router.get("/api/session/{session_id}/voice-activity")
async def get_voice_activity(session_id: str, request: Request):
    """Poll during voice: server-side webhook + pipeline steps."""
    ensure_session_id(session_id)
    session = await request.app.state.store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "items": [i.model_dump(mode="json") for i in session.voice_activity],
    }
