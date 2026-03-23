import uuid
from typing import Any

from pydantic import BaseModel, Field
from datetime import datetime


class VoiceActivityItem(BaseModel):
    """Append-only feed for voice UI (webhooks + optional client mirror)."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: datetime = Field(default_factory=datetime.now)
    event: str
    title: str
    detail: str = ""
    data: dict[str, Any] | None = None


class ResearchSource(BaseModel):
    """One page or result used to build the report (from web search)."""

    title: str = ""
    url: str = ""
    topic: str = ""  # short label, e.g. which search theme this came from


class JobTaskExposure(BaseModel):
    """One concrete work task with time share and automation exposure (from Claude task decomposition)."""

    task: str = ""
    time_pct: int = 0  # ~% of workweek; server clamps
    automation_score_0_100: int = 50
    reasoning: str = ""
    timeline_horizon: str = "longer"  # now | 1_2_years | 3_5_years | longer


class UserProfile(BaseModel):
    name: str
    degree: str
    university: str
    graduation_year: int
    current_job: str
    current_company: str = ""
    salary: int | None = None
    years_experience: int | None = Field(
        default=None,
        description="Years in role or field; improves AI risk + safeguard tailoring.",
    )
    # Voice agent sets these when the user gives a region (e.g. UK + £60k → GBP).
    country_or_region: str = ""
    currency_code: str = Field(
        default="USD",
        description="ISO 4217: USD, GBP, EUR, etc. All salary/tuition integers use this currency.",
    )
    source: str = "manual"


class ResearchData(BaseModel):
    currency_code: str = Field(
        default="USD",
        description="ISO 4217 for all monetary fields in this object.",
    )
    avg_salary_for_degree: int | None = None
    avg_salary_for_role: int | None = None
    median_salary_for_role: int | None = None
    salary_range_low: int | None = None
    salary_range_high: int | None = None
    estimated_tuition: int | None = None
    tuition_if_invested: int | None = None
    tuition_opportunity_gap: int | None = None
    degree_roi_rank: str | None = None
    job_market_trend: str | None = None
    unemployment_rate_pct: float | None = None
    job_openings_estimate: int | None = None
    raw_search_results: list[str] = []
    sources: list[ResearchSource] = Field(default_factory=list)
    named_sources: list[str] = Field(
        default_factory=list,
        description="Organizations named in snippets (e.g. BLS, Glassdoor), from AI extraction.",
    )
    methodology_note: str = ""
    search_queries: list[str] = Field(
        default_factory=list,
        description="Firecrawl search strings used for this run (voice activity UI).",
    )
    search_hit_counts: list[int] = Field(
        default_factory=list,
        description="Parallel to search_queries: raw result rows with text per query.",
    )

    # S&P 500 financial model
    sp500_annual_return_pct: float | None = None
    sp500_total_return_pct: float | None = None
    tuition_as_sp500_today: int | None = None
    years_since_graduation: int | None = None
    lifetime_earnings_estimate: int | None = None
    degree_premium_over_hs: int | None = None

    ai_replacement_risk_0_100: int | None = None
    ai_risk_reasoning: str = ""
    overall_cooked_0_100: int | None = None
    # Task decomposition (optional): when present, ai_replacement_risk_0_100 is time-weighted from tasks.
    job_task_exposure: list[JobTaskExposure] = Field(default_factory=list)
    near_term_ai_risk_0_100: int | None = Field(
        None,
        description="AI exposure in ~0–2y horizon from tasks with timeline now/1_2_years only.",
    )
    # Cooked meter components (higher = worse). overall_cooked blends these with AI risk.
    career_market_stress_0_100: int | None = Field(
        None,
        description="Job market / trajectory stress from trend + unemployment.",
    )
    financial_roi_stress_0_100: int | None = Field(
        None,
        description="Tuition vs index opportunity-cost stress.",
    )
    safeguard_tips: list[str] = []
    honest_take: str = ""


class ReportCard(BaseModel):
    session_id: str
    grade: str
    grade_score: int
    profile: UserProfile
    research: ResearchData
    roast_quote: str = ""


class Session(BaseModel):
    session_id: str
    profile: UserProfile
    research: ResearchData | None = None
    report_card: ReportCard | None = None
    created_at: datetime
    voice_activity: list[VoiceActivityItem] = Field(default_factory=list)
