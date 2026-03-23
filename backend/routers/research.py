from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from backend.services.firecrawl_service import run_research
from backend.services.grading import compute_grade
from backend.models import ReportCard
from backend.routers.webhooks import ResearchProfilePayload

router = APIRouter()


class ResearchRequest(BaseModel):
    session_id: str
    profile: ResearchProfilePayload | None = None


@router.post("/api/research")
async def do_research(req: ResearchRequest, request: Request):
    store = request.app.state.store
    session = store.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    p = req.profile.to_user_profile() if req.profile is not None else session.profile
    research = await run_research(
        degree=p.degree,
        university=p.university,
        graduation_year=p.graduation_year,
        current_job=p.current_job,
        years_experience=p.years_experience,
        salary=p.salary,
        country_or_region=p.country_or_region,
        currency_code=p.currency_code,
    )
    store.update_research(req.session_id, research)

    p = p.model_copy(update={"currency_code": research.currency_code})

    grade, score = compute_grade(research, p.salary, p.years_experience)
    report_card = ReportCard(
        session_id=req.session_id,
        grade=grade,
        grade_score=score,
        profile=p,
        research=research,
    )
    store.update_report_card(req.session_id, report_card)

    return {"research": research.model_dump(), "grade": grade, "score": score}
