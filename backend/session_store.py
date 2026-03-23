import uuid
from datetime import datetime

from backend.database import get_async_firestore
from backend.models import Session, UserProfile, ResearchData, ReportCard, VoiceActivityItem
from backend.repositories.session_repo import AsyncSessionRepository


class SessionStore:
    """
    Session persistence: Firestore when configured, else in-memory dict.
    All methods are async for FastAPI compatibility.
    """

    def __init__(self) -> None:
        self._memory: dict[str, Session] = {}
        self._db = get_async_firestore()
        self._repo: AsyncSessionRepository | None = (
            AsyncSessionRepository(self._db) if self._db else None
        )

    @property
    def uses_firestore(self) -> bool:
        return self._repo is not None

    async def create(self, profile: UserProfile) -> str:
        if self._repo:
            return await self._repo.create(profile)
        session_id = str(uuid.uuid4())
        self._memory[session_id] = Session(
            session_id=session_id,
            profile=profile,
            created_at=datetime.now(),
        )
        return session_id

    async def get(self, session_id: str) -> Session | None:
        if self._repo:
            return await self._repo.get(session_id)
        return self._memory.get(session_id)

    async def update_research(self, session_id: str, research: ResearchData) -> None:
        if self._repo:
            await self._repo.update_research(session_id, research)
            return
        session = self._memory.get(session_id)
        if session:
            session.research = research

    async def update_report_card(self, session_id: str, report_card: ReportCard) -> None:
        if self._repo:
            await self._repo.update_report_card(session_id, report_card)
            return
        session = self._memory.get(session_id)
        if session:
            session.report_card = report_card

    async def update_roast_quote(self, session_id: str, quote: str) -> None:
        if self._repo:
            await self._repo.update_roast_quote(session_id, quote)
            return
        session = self._memory.get(session_id)
        if session and session.report_card:
            session.report_card.roast_quote = quote

    async def patch_profile(self, session_id: str, updates: dict) -> bool:
        if self._repo:
            return await self._repo.patch_profile(session_id, updates)
        session = self._memory.get(session_id)
        if not session:
            return False
        allowed = set(UserProfile.model_fields.keys())
        filtered = {k: v for k, v in updates.items() if k in allowed}
        if not filtered:
            return True
        session.profile = session.profile.model_copy(update=filtered)
        return True

    async def append_voice_activity(
        self,
        session_id: str,
        *,
        event: str,
        title: str,
        detail: str = "",
        data: dict | None = None,
    ) -> None:
        if self._repo:
            await self._repo.append_voice_activity(
                session_id,
                event=event,
                title=title,
                detail=detail,
                data=data,
            )
            return
        session = self._memory.get(session_id)
        if not session:
            return
        session.voice_activity.append(
            VoiceActivityItem(event=event, title=title, detail=detail, data=data)
        )
        if len(session.voice_activity) > 120:
            session.voice_activity[:] = session.voice_activity[-120:]