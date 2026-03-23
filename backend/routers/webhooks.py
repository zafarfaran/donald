import asyncio
import os

import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.services.firecrawl_service import run_research, resolve_research_query_plan
from backend.services.money_locale import normalize_currency_code
from backend.services.research_outcome import (
    apply_cooked_components,
    grade_and_report_card,
    tuition_invested_for_api as _tuition_invested_for_api,
)
from backend.models import ReportCard, ResearchData, UserProfile
from backend.session_id import ensure_session_id

router = APIRouter()
logger = structlog.get_logger(__name__)

VOICE_RESEARCH_DEADLINE_SEC = float(os.getenv("VOICE_RESEARCH_DEADLINE_SEC", "270"))


def _profile_blurb(p: UserProfile) -> str:
    parts = [p.degree or "—", p.university or "—", p.current_job or "—"]
    return " · ".join(parts)


def _voice_research_profile_errors(p: UserProfile) -> str | None:
    """Light validation so the agent gets a spoken retry message."""
    if not (p.degree or "").strip():
        return "Missing degree — ask what they studied, then call research_degree again."
    if not (p.university or "").strip():
        return "Missing school or university — ask where they studied, then call research_degree again."
    if not (p.current_job or "").strip():
        return (
            "Missing current situation — ask their job title, student status, or what they're aiming for, "
            "then call research_degree again."
        )
    return None


def _truncate(s: str, n: int = 220) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


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
            "tuition_paid": p.tuition_paid,
            "tuition_is_total": p.tuition_is_total,
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
            "tuition_web_estimate": research.tuition_web_estimate,
            "tuition_if_invested": _tuition_invested_for_api(research),
            "ai_replacement_risk_0_100": research.ai_replacement_risk_0_100,
            "near_term_ai_risk_0_100": research.near_term_ai_risk_0_100,
            "career_market_stress_0_100": research.career_market_stress_0_100,
            "financial_roi_stress_0_100": research.financial_roi_stress_0_100,
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
    tuition_paid: int | None = Field(None, alias="tuitionPaid")
    tuition_is_total: bool = Field(True, alias="tuitionIsTotal")
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

    @field_validator("tuition_paid", mode="before")
    @classmethod
    def _coerce_tuition(cls, v: object) -> int | None:
        if v is None or v == "":
            return None
        if isinstance(v, bool):
            return None
        if isinstance(v, int):
            return v if v > 0 else None
        s = str(v).strip().replace(",", "")
        if not s:
            return None
        try:
            n = int(float(s))
        except ValueError:
            return None
        return n if n > 0 else None

    @field_validator("tuition_is_total", mode="before")
    @classmethod
    def _coerce_tuition_is_total(cls, v: object) -> bool:
        if isinstance(v, bool):
            return v
        if v is None or v == "":
            return True
        s = str(v).strip().lower()
        if s in {"false", "0", "no", "annual", "per year", "yearly"}:
            return False
        return True

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
    tuition_paid: int | None = Field(None, alias="tuitionPaid")
    tuition_is_total: bool | None = Field(None, alias="tuitionIsTotal")
    source: str | None = None


@router.post("/api/webhooks/get_user_profile")
async def webhook_get_profile(req: WebhookRequest, request: Request):
    ensure_session_id(req.session_id)
    store = request.app.state.store
    session = await store.get(req.session_id)
    if not session:
        return {"error": "Session not found"}
    p = session.profile
    await store.append_voice_activity(
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
    ensure_session_id(req.session_id)
    store = request.app.state.store
    patch = req.model_dump(exclude={"session_id"}, exclude_unset=True)
    if not await store.patch_profile(req.session_id, patch):
        return {"error": "Session not found", "ok": False}
    session = await store.get(req.session_id)
    if not session:
        return {"error": "Session not found", "ok": False}
    p = session.profile
    keys = ", ".join(sorted(patch.keys())) if patch else "(no profile fields — agent may have skipped tool args or used wrong keys)"
    await store.append_voice_activity(
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
    ensure_session_id(req.session_id)
    store = request.app.state.store
    session = await store.get(req.session_id)
    if not session:
        return {
            "error": "Session not found",
            "research_complete": False,
            "agent_note": "Research did not run — session missing. Ask the user to restart the call from the app.",
        }

    p = req.profile.to_user_profile()
    if err := _voice_research_profile_errors(p):
        return {
            "error": err,
            "research_complete": False,
            "agent_note": err,
        }
    # Privacy: voice flow does not merge into session.profile; only report_card holds a snapshot for the UI.
    rq, _, _, _ = resolve_research_query_plan(
        p.degree,
        p.university,
        p.graduation_year,
        p.current_job,
        country_or_region=p.country_or_region,
        currency_code=p.currency_code,
    )
    await store.append_voice_activity(
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
                tuition_paid=p.tuition_paid,
                tuition_is_total=p.tuition_is_total,
            ),
            timeout=VOICE_RESEARCH_DEADLINE_SEC,
        )
    except asyncio.TimeoutError:
        logger.error(
            "research_degree_timeout",
            deadline_sec=VOICE_RESEARCH_DEADLINE_SEC,
            session_prefix=req.session_id[:8],
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
    research = apply_cooked_components(research)
    await store.update_research(req.session_id, research)
    grade, score, report_card = grade_and_report_card(req.session_id, p, research)
    await store.update_report_card(req.session_id, report_card)

    await store.append_voice_activity(
        req.session_id,
        event="webhook_research_complete",
        title="Numbers are back",
        detail="Donald has your snapshot. Full breakdown is on the report page.",
        data=_voice_research_complete_payload(research, grade, score),
    )

    return {
        # Voice agent: receiving this object means research is DONE — do not wait for the user to say "ready".
        "research_complete": True,
        "agent_note": (
            "This tool result is the full research output. Pipeline finished successfully. "
            "When stating ANY number the user will also see on their report card, use **report_numbers** below with **report_numbers.currency_code** — do not round differently or swap median vs average. "
            "Treat any numbers inside ai_risk_reasoning or honest_take as narrative context only; for spoken figures always read from report_numbers. "
            f"Canonical AI exposure to speak is exactly {research.ai_replacement_risk_0_100}/100 from report_numbers.ai_replacement_risk_0_100. "
            "Phase 3: roast monologue using grade and fields below — start immediately; do NOT ask the user to confirm research. "
            "Phase 4: explain safeguard_tips as ordered top moves — what to do + brief why each matters for this user; close with 'if you only do one thing…' (paraphrase; do not invent tips). "
            "Then save_roast_quote with your best roast one-liner from Phase 3 only, then follow-ups."
        ),
        "report_numbers": {
            "currency_code": research.currency_code,
            "estimated_tuition": research.estimated_tuition,
            "tuition_web_estimate": research.tuition_web_estimate,
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
            "near_term_ai_risk_0_100": research.near_term_ai_risk_0_100,
            "career_market_stress_0_100": research.career_market_stress_0_100,
            "financial_roi_stress_0_100": research.financial_roi_stress_0_100,
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
        # Tuition + S&P 500 financial model (canonical fields only)
        "estimated_tuition": research.estimated_tuition,
        "tuition_web_estimate": research.tuition_web_estimate,
        "tuition_if_invested": _tuition_invested_for_api(research),
        "tuition_opportunity_gap": research.tuition_opportunity_gap,
        "sp500_annual_return_pct": research.sp500_annual_return_pct,
        "sp500_total_return_pct": research.sp500_total_return_pct,
        "years_since_graduation": research.years_since_graduation,
        # Career
        "degree_roi_rank": research.degree_roi_rank,
        "job_market_trend": research.job_market_trend,
        "unemployment_rate_pct": research.unemployment_rate_pct,
        "job_openings_estimate": research.job_openings_estimate,
        "lifetime_earnings_estimate": research.lifetime_earnings_estimate,
        "degree_premium_over_hs": research.degree_premium_over_hs,
        # AI risk
        "ai_replacement_risk_0_100": research.ai_replacement_risk_0_100,
        "ai_risk_reasoning": research.ai_risk_reasoning,
        "near_term_ai_risk_0_100": research.near_term_ai_risk_0_100,
        "career_market_stress_0_100": research.career_market_stress_0_100,
        "financial_roi_stress_0_100": research.financial_roi_stress_0_100,
        "overall_cooked_0_100": research.overall_cooked_0_100,
        "job_task_exposure": [t.model_dump() for t in research.job_task_exposure],
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
    ensure_session_id(req.session_id)
    store = request.app.state.store
    await store.update_roast_quote(req.session_id, req.quote)
    await store.append_voice_activity(
        req.session_id,
        event="webhook_save_roast_quote",
        title="Your best line is saved",
        detail=_truncate(req.quote, 300),
    )
    return {"saved": True}
