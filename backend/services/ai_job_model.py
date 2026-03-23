"""
Heuristics for AI replacement risk, overall 'cooked' score, and safeguard tips.
Uses job title + search snippets + experience. No extra API keys required.
"""

from __future__ import annotations

import re

# Rough baseline: how automatable typical tasks for this role family are (0 = safer, 100 = very exposed)
_ROLE_KEYWORDS: list[tuple[list[str], int]] = [
    (["data entry", "transcription", "call center", "telemarketer", "cashier"], 88),
    (["paralegal", "legal assistant", "bookkeeper", "payroll clerk", "accounting clerk"], 78),
    (["customer service", "support agent", "help desk", "receptionist"], 72),
    (["journalist", "reporter", "copywriter", "content writer", "social media"], 68),
    (["marketing", "seo", "graphic design", "designer"], 62),
    (["analyst", "financial analyst", "research analyst"], 58),
    (["software", "developer", "engineer", "programmer"], 55),
    (["hr ", "recruiter", "human resources"], 52),
    (["sales", "account executive", "bd "], 48),
    (["teacher", "professor", "instructor"], 42),
    (["nurse", "rn ", "therapist", "counselor", "social worker"], 35),
    (["electrician", "plumber", "hvac", "welder", "mechanic"], 28),
    (["surgeon", "physician", "doctor", "dentist"], 22),
]

_HIGH_RISK_PHRASES = [
    "high risk of automation",
    "likely to be automated",
    "replaced by ai",
    "replaced by chatgpt",
    "generative ai",
    "already automating",
    "job losses from ai",
    "vulnerable to automation",
    "routine tasks automated",
]

_LOWER_RISK_PHRASES = [
    "low risk of automation",
    "difficult to automate",
    "human judgment",
    "requires empathy",
    "physical presence",
    "hands-on",
    "creative work",
    "strategic role",
    "regulated profession",
]


def _baseline_risk_from_job_title(job_title: str) -> int:
    j = job_title.lower().strip()
    if not j:
        return 55
    for keywords, risk in _ROLE_KEYWORDS:
        if any(k in j for k in keywords):
            return risk
    return 52


def _snippet_adjustment(combined_text: str) -> int:
    """Delta roughly in [-18, 18] added to baseline risk."""
    if not combined_text:
        return 0
    t = combined_text.lower()
    high = sum(1 for p in _HIGH_RISK_PHRASES if p in t)
    low = sum(1 for p in _LOWER_RISK_PHRASES if p in t)
    # Extra weight if "automation" and "risk" co-occur near each other
    if re.search(r"automation.{0,40}risk|risk.{0,40}automation", t):
        high += 1
    return min(18, max(-18, high * 6 - low * 5))


def adjust_risk_for_experience(risk_0_100: int, years: int | None) -> int:
    """Junior roles often have more routine tasks; seniority adds tacit judgment."""
    if years is None:
        return risk_0_100
    y = max(0, min(years, 40))
    if y <= 2:
        return min(100, risk_0_100 + 8)
    if y <= 5:
        return risk_0_100
    if y <= 12:
        return max(0, risk_0_100 - 5)
    return max(0, risk_0_100 - 12)


def infer_ai_replacement_risk(
    job_title: str,
    combined_snippets: str,
    years_experience: int | None,
) -> int:
    base = _baseline_risk_from_job_title(job_title)
    adjusted = base + _snippet_adjustment(combined_snippets)
    adjusted = adjust_risk_for_experience(adjusted, years_experience)
    return max(0, min(100, adjusted))


def _trend_stress_0_100(job_market_trend: str | None) -> int:
    if job_market_trend == "shrinking":
        return 85
    if job_market_trend == "flat":
        return 55
    if job_market_trend == "growing":
        return 30
    return 50


def _financial_stress_0_100(
    estimated_tuition: int | None,
    tuition_if_invested: int | None,
) -> int:
    if not estimated_tuition or estimated_tuition <= 0:
        return 40
    if not tuition_if_invested:
        return 45
    gap = tuition_if_invested - estimated_tuition
    if gap <= 0:
        return 25
    ratio = gap / estimated_tuition
    return min(100, int(35 + ratio * 25))


def compute_overall_cooked_0_100(
    ai_replacement_risk_0_100: int,
    job_market_trend: str | None,
    estimated_tuition: int | None,
    tuition_if_invested: int | None,
) -> int:
    """
    Single 'how cooked' number: job+AI exposure, market, and tuition regret.
    Higher = worse position.
    Strict band: AI replacement above 70% means you're at least that 'cooked' on the meter.
    """
    t = _trend_stress_0_100(job_market_trend)
    f = _financial_stress_0_100(estimated_tuition, tuition_if_invested)
    raw = 0.55 * ai_replacement_risk_0_100 + 0.25 * t + 0.20 * f
    out = max(0, min(100, int(round(raw))))
    if ai_replacement_risk_0_100 > 70:
        # Never show 'overall cooked' below AI risk when automation exposure is high
        out = max(out, ai_replacement_risk_0_100)
    return out


def build_safeguard_tips(
    job_title: str,
    degree: str,
    ai_risk_0_100: int,
    years_experience: int | None,
) -> list[str]:
    """Actionable, non-legal-advice suggestions tailored to risk band."""
    tips: list[str] = []
    j = job_title.strip() or "your role"
    d = degree.strip() or "your field"

    if ai_risk_0_100 >= 70:
        tips.append(
            f"Treat {j} as a stack: document what only you decide (judgment, stakeholders, edge cases) and push everything else into repeatable playbooks."
        )
        tips.append(
            "Pick one AI tool you actually ship with weekly (not just ChatGPT) — prompts, evals, and review — so you become the person who automates the work, not the one replaced by it."
        )
        tips.append(
            f"Add a scarce combo: {d} + domain depth (industry cert, regulated context, or revenue ownership) so you're harder to swap for a generic model."
        )
    elif ai_risk_0_100 >= 45:
        tips.append(
            "Move up the value chain: own outcomes (pipeline, P&L, launches) not just outputs (docs, tickets, slides)."
        )
        tips.append(
            "Build a public or internal portfolio of before/after work where AI sped you up — proof you multiply output."
        )
        tips.append(
            "Schedule a quarterly 'task audit': list what you do monthly and tag each as automate / augment / human-only."
        )
    else:
        tips.append(
            "Still worth automating your own busywork — frees time for higher-leverage problems only you can take."
        )
        tips.append(
            "Keep a living skills map for your team: who covers judgment, compliance, and client trust when tools change."
        )

    if years_experience is not None and years_experience < 4:
        tips.append(
            "Early-career: prioritize mentorship paths and roles where you touch customers, decisions, or production systems — not only task queues."
        )
    else:
        tips.append(
            "Leverage experience: write short decision memos or runbooks others follow — that's leverage AI can't copy without you."
        )

    tips.append(
        "Follow one serious source on AI + labor in your industry (reports, regulator notes, or union/pro society briefs) — narratives move faster than models."
    )
    return tips[:6]


def financial_opportunity_gap(
    estimated_tuition: int | None,
    tuition_if_invested: int | None,
) -> int | None:
    """How much more you'd have had if tuition went to markets (same formula as UI narrative)."""
    if estimated_tuition is None or tuition_if_invested is None:
        return None
    return tuition_if_invested - estimated_tuition
