import uuid
from datetime import datetime
from backend.models import Session, UserProfile, ResearchData, ReportCard, VoiceActivityItem


class SessionStore:
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create(self, profile: UserProfile) -> str:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = Session(
            session_id=session_id,
            profile=profile,
            created_at=datetime.now(),
        )
        return session_id

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def update_research(self, session_id: str, research: ResearchData) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.research = research

    def update_report_card(self, session_id: str, report_card: ReportCard) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.report_card = report_card

    def update_roast_quote(self, session_id: str, quote: str) -> None:
        session = self._sessions.get(session_id)
        if session and session.report_card:
            session.report_card.roast_quote = quote

    def patch_profile(self, session_id: str, updates: dict) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        allowed = set(UserProfile.model_fields.keys())
        filtered = {k: v for k, v in updates.items() if k in allowed}
        if not filtered:
            return True
        session.profile = session.profile.model_copy(update=filtered)
        return True

    def append_voice_activity(
        self,
        session_id: str,
        *,
        event: str,
        title: str,
        detail: str = "",
        data: dict | None = None,
    ) -> None:
        session = self._sessions.get(session_id)
        if not session:
            return
        session.voice_activity.append(
            VoiceActivityItem(event=event, title=title, detail=detail, data=data)
        )
        if len(session.voice_activity) > 120:
            session.voice_activity[:] = session.voice_activity[-120:]
