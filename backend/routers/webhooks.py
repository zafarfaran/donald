import asyncio
import logging
import os

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.services.firecrawl_service import run_research, resolve_research_query_plan
from backend.services.money_locale import normalize_currency_code
from backend.services.grading import compute_grade
from backend.services.ai_job_model import compute_overall_cooked_0_100
from backend.models import ReportCard, ResearchData, UserProfile

router = APIRouter()
logger = logging.getLogger(__name__)

VOICE_RESEARCH_DEADLINE_SEC = float(os.getenv("VOICE_RESEARCH_DEADLINE_SEC", "270"))


def _profile_blurb(p: UserProfile) -> str:
    parts = [p.degree or "—", p.university or "—", p.current_job or "—"]
    return " · ".join(parts)


def _truncate(s: str, n: int = 220) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _tuition_invested_for_api(r: ResearchData) -> int | None:
    """Same value the report card shows for 'If You'd Invested' / opportunity-cost column."""
    if r.tuition_if_invested is not None:
        return r.tuition_if_invested
    return r.tuition_as_sp500_today


def _voice_research_started_payload(p: UserProfile, queries: list[str]) -> dict:
    return {
        "step": "research_started",
        "note": "Hang tight — we're checking salaries, tuition, and job-market signals for your roast.",
        "query_count": len(queries),
        "queries": queries,
        "profile": {
            "degree": p.degree,
            "university": p.university,
            "graduation_year": p.graduation_year,
            "current_job": p.current_job,
            "currency_code": p.currency_code,
            "country_or_region": p.country_or_region,
        },
    }


def _voice_research_complete_payload(research: ResearchData, grade: str, score: int) -> dict:
    hits = research.search_hit_counts or []
    total_hits = sum(hits) if hits else 0
    return {
        "step": "research_complete",
        "grade": grade,
        "grade_score": score,
        "currency_code": research.currency_code,
        "query_count": len(research.search_queries),
        "total_snippet_hits": total_hits,
        "hits_per_query": hits,
        "queries": research.search_queries,
        "key_numbers": {
            "avg_salary_for_degree": research.avg_salary_for_degree,
            "avg_salary_for_role": research.avg_salary_for_role,
            "median_salary_for_role": research.median_salary_for_role,
            "estimated_tuition": research.estimated_tuition,
            "tuition_if_invested": _tuition_invested_for_api(research),
            "ai_replacement_risk_0_100": research.ai_replacement_risk_0_100,
            "overall_cooked_0_100": research.overall_cooked_0_100,
            "job_market_trend": research.job_market_trend,
        },
        "sources": [s.model_dump() for s in research.sources[:12]],
        "named_sources": research.named_sources[:12],
    }


class WebhookRequest(BaseModel):
    session_id: str


class ResearchProfilePayload(BaseModel):
    """Inline profile for voice: not read from session store. Becomes the snapshot on ReportCard only."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str = ""
    degree: str = ""
    university: str = ""
    graduation_year: int = 0
    current_job: str = ""
    current_company: str = ""
    salary: int | None = None
    years_experience: int | None = Field(None, alias="yearsExperience")
    country_or_region: str = Field("", alias="countryOrRegion")
    currency_code: str = Field("USD", alias="currencyCode")
    source: str = "voice"

    @field_validator("currency_code", mode="before")
    @classmethod
    def _normalize_currency_code(cls, v: object) -> str:
        if v is None or v == "":
            return "USD"
        return normalize_currency_code(str(v).strip())

    @field_validator("country_or_region", mode="before")
    @classmethod
    def _strip_country(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v).strip()

    def to_user_profile(self) -> UserProfile:
        return UserProfile(**self.model_dump(by_alias=False))


class ResearchDegreeWebhookRequest(BaseModel):
    session_id: str
    profile: ResearchProfilePayload


class SaveQuoteRequest(BaseModel):
    session_id: str
    quote: str


class UpdateUserProfileRequest(BaseModel):
    """Merge fields into the session profile (omit keys you are not setting). Voice agents call this after extracting answers, then call research_degree."""

    model_config = ConfigDict(populate_by_name=True)

    session_id: str
    name: str | None = None
    degree: str | None = None
    university: str | None = None
    graduation_year: int | None = Field(None, alias="graduationYear")
    current_job: str | None = Field(None, alias="currentJob")
    current_company: str | None = Field(None, alias="currentCompany")
    salary: int | None = None
    years_experience: int | None = Field(None, alias="yearsExperience")
    country_or_region: str | None = Field(None, alias="countryOrRegion")
    currency_code: str | None = Field(None, alias="currencyCode")
    source: str | None = None


@router.post("/api/webhooks/get_user_profile")
async def webhook_get_profile(req: WebhookRequest, request: Request):
    store = request.app.state.store
    session = store.get(req.session_id)
    if not session:
        return {"error": "Session not found"}
    p = session.profile
    store.append_voice_activity(
        req.session_id,
        event="webhook_get_user_profile",
        title="Profile loaded",
        detail=_profile_blurb(p),
        data={
            "degree": p.degree,
            "university": p.university,
            "graduation_year": p.graduation_year,
            "current_job": p.current_job,
        },
    )
    return {
        "name": p.name,
        "degree": p.degree,
        "university": p.university,
        "graduation_year": p.graduation_year,
        "current_job": p.current_job,
        "current_company": p.current_company,
        "salary": p.salary,
        "years_experience": p.years_experience,
        "country_or_region": p.country_or_region,
        "currency_code": p.currency_code,
    }


@router.post("/api/webhooks/update_user_profile")
async def webhook_update_profile(req: UpdateUserProfileRequest, request: Request):
    store = request.app.state.store
    patch = req.model_dump(exclude={"session_id"}, exclude_unset=True)
    if not store.patch_profile(req.session_id, patch):
        return {"error": "Session not found", "ok": False}
    session = store.get(req.session_id)
    if not session:
        return {"error": "Session not found", "ok": False}
    p = session.profile
    keys = ", ".join(sorted(patch.keys())) if patch else "(no profile fields — agent may have skipped tool args or used wrong keys)"
    store.append_voice_activity(
        req.session_id,
        event="webhook_update_user_profile",
        title="Profile updated from voice" if patch else "Profile merge (empty patch)",
        detail=keys,
        data=patch if patch else None,
    )
    return {
        "ok": True,
        "name": p.name,
        "degree": p.degree,
        "university": p.university,
        "graduation_year": p.graduation_year,
        "current_job": p.current_job,
        "current_company": p.current_company,
        "salary": p.salary,
        "years_experience": p.years_experience,
        "country_or_region": p.country_or_region,
        "currency_code": p.currency_code,
        "source": p.source,
    }


@router.post("/api/webhooks/research_degree")
async def webhook_research(req: ResearchDegreeWebhookRequest, request: Request):
    store = request.app.state.store
    session = store.get(req.session_id)
    if not session:
        return {
            "error": "Session not found",
            "research_complete": False,
            "agent_note": "Research did not run — session missing. Ask the user to restart the call from the app.",
        }

    p = req.profile.to_user_profile()
    # Privacy: voice flow does not merge into session.profile; only report_card holds a snapshot for the UI.
    rq, _, _, _ = resolve_research_query_plan(
        p.degree,
        p.university,
        p.graduation_year,
        p.current_job,
        country_or_region=p.country_or_region,
        currency_code=p.currency_code,
    )
    store.append_voice_activity(
        req.session_id,
        event="webhook_research_started",
        title="Looking up your degree story",
        detail=(
            f"Running about {len(rq)} checks — can take a couple of minutes. "
            "Stay on this tab; Donald will pick up when it’s done."
        ),
        data=_voice_research_started_payload(p, rq),
    )
    try:
        research = await asyncio.wait_for(
            run_research(
                degree=p.degree,
                university=p.university,
                graduation_year=p.graduation_year,
                current_job=p.current_job,
                years_experience=p.years_experience,
                salary=p.salary,
                country_or_region=p.country_or_region,
                currency_code=p.currency_code,
            ),
            timeout=VOICE_RESEARCH_DEADLINE_SEC,
        )
    except asyncio.TimeoutError:
        logger.error(
            "research_degree exceeded VOICE_RESEARCH_DEADLINE_SEC=%s for session %s",
            VOICE_RESEARCH_DEADLINE_SEC,
            req.session_id[:8],
        )
        return {
            "error": (
                f"Research timed out after {int(VOICE_RESEARCH_DEADLINE_SEC)} seconds. "
                "Try again, or set FIRECRAWL_SEARCH_TIMEOUT_MS / VOICE_RESEARCH_DEADLINE_SEC if your network is slow."
            ),
            "research_complete": False,
            "agent_note": (
                "Research did not finish in time — do not roast with made-up numbers. "
                "Apologize briefly, ask them to try again, and offer to retry research_degree."
            ),
        }
    # Report card + voice must share the same money fields; refresh cooked score with current rules
    if research.tuition_if_invested is None and research.tuition_as_sp500_today is not None:
        research = research.model_copy(update={"tuition_if_invested": research.tuition_as_sp500_today})
    if research.ai_replacement_risk_0_100 is not None:
        research = research.model_copy(
            update={
                "overall_cooked_0_100": compute_overall_cooked_0_100(
                    research.ai_replacement_risk_0_100,
                    research.job_market_trend,
                    research.estimated_tuition,
                    _tuition_invested_for_api(research),
                )
            }
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

    store.append_voice_activity(
        req.session_id,
        event="webhook_research_complete",
        title=f"All set — grade {grade}",
        detail=_truncate(
            research.honest_take
            or research.ai_risk_reasoning
            or "Your report card is ready. Donald has what he needs to roast you fairly."
        ),
        data=_voice_research_complete_payload(research, grade, score),
    )

    return {
        # Voice agent: receiving this object means research is DONE — do not wait for the user to say "ready".
        "research_complete": True,
        "agent_note": (
            "This tool result is the full research output. Pipeline finished successfully. "
            "When stating ANY number the user will also see on their report card, use **report_numbers** below with **report_numbers.currency_code** — do not round differently or swap median vs average. "
            "Phase 3: roast monologue using grade and fields below — start immediately; do NOT ask the user to confirm research. "
            "Phase 4: explain safeguard_tips as ordered top moves — what to do + brief why each matters for this user; close with 'if you only do one thing…' (paraphrase; do not invent tips). "
            "Then save_roast_quote with your best roast one-liner from Phase 3 only, then follow-ups."
        ),
        "report_numbers": {
            "currency_code": research.currency_code,
            "estimated_tuition": research.estimated_tuition,
            "tuition_if_invested": _tuition_invested_for_api(research),
            "tuition_opportunity_gap": research.tuition_opportunity_gap,
            "avg_salary_for_degree": research.avg_salary_for_degree,
            "avg_salary_for_role": research.avg_salary_for_role,
            "median_salary_for_role": research.median_salary_for_role,
            "salary_range_low": research.salary_range_low,
            "salary_range_high": research.salary_range_high,
            "degree_roi_rank": research.degree_roi_rank,
            "job_market_trend": research.job_market_trend,
            "ai_replacement_risk_0_100": research.ai_replacement_risk_0_100,
            "overall_cooked_0_100": research.overall_cooked_0_100,
            "grade": grade,
            "grade_score": score,
        },
        "grade": grade,
        "grade_score": score,
        # Salary
        "avg_salary_for_degree": research.avg_salary_for_degree,
        "avg_salary_for_role": research.avg_salary_for_role,
        "median_salary_for_role": research.median_salary_for_role,
        "salary_range_low": research.salary_range_low,
        "salary_range_high": research.salary_range_high,
        # Tuition + S&P 500 financial model (aliases + canonical names = report card JSON)
        "tuition_estimated": research.estimated_tuition,
        "tuition_if_invested_in_sp500": _tuition_invested_for_api(research),
        "estimated_tuition": research.estimated_tuition,
        "tuition_if_invested": _tuition_invested_for_api(research),
        "tuition_opportunity_gap": research.tuition_opportunity_gap,
        "sp500_annual_return_pct": research.sp500_annual_return_pct,
        "sp500_total_return_pct": research.sp500_total_return_pct,
        "years_since_graduation": research.years_since_graduation,
        # Career
        "roi_rank": research.degree_roi_rank,
        "job_trend": research.job_market_trend,
        "degree_roi_rank": research.degree_roi_rank,
        "job_market_trend": research.job_market_trend,
        "unemployment_rate_pct": research.unemployment_rate_pct,
        "job_openings_estimate": research.job_openings_estimate,
        "lifetime_earnings_estimate": research.lifetime_earnings_estimate,
        "degree_premium_over_hs": research.degree_premium_over_hs,
        # AI risk
        "ai_replacement_risk_0_100": research.ai_replacement_risk_0_100,
        "ai_risk_reasoning": research.ai_risk_reasoning,
        "overall_cooked_0_100": research.overall_cooked_0_100,
        # Analysis
        "safeguard_tips": research.safeguard_tips,
        "honest_take": research.honest_take,
        "roast_ammo": research.raw_search_results[:5],
        "sources": [s.model_dump() for s in research.sources],
        "named_sources": research.named_sources,
        "methodology_note": research.methodology_note,
        "currency_code": research.currency_code,
        "search_queries": research.search_queries,
        "search_hit_counts": research.search_hit_counts,
    }


@router.post("/api/webhooks/save_roast_quote")
async def webhook_save_quote(req: SaveQuoteRequest, request: Request):
    store = request.app.state.store
    store.update_roast_quote(req.session_id, req.quote)
    store.append_voice_activity(
        req.session_id,
        event="webhook_save_roast_quote",
        title="Your best line is saved",
        detail=_truncate(req.quote, 300),
    )
    return {"saved": True}
