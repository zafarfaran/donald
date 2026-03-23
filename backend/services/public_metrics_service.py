from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.database import get_async_firestore, get_sync_firestore
from backend.models import ReportCard, ResearchData, Session, UserProfile

METRICS_COLLECTION = "public_metrics"
METRICS_DOC_ID = "homepage"
SESSIONS_COLLECTION = "sessions"


def _session_to_firestore_doc(session: Session) -> dict[str, Any]:
    return {
        "profile": session.profile.model_dump(mode="json"),
        "research": session.research.model_dump(mode="json") if session.research else None,
        "report_card": session.report_card.model_dump(mode="json") if session.report_card else None,
        "created_at": session.created_at,
        "voice_activity": [i.model_dump(mode="json") for i in session.voice_activity],
    }


def _format_compact_usd(n: int) -> str:
    sign = "-" if n < 0 else ""
    x = abs(n)
    if x >= 1_000_000_000:
        return f"{sign}${x / 1_000_000_000:.1f}B"
    if x >= 1_000_000:
        return f"{sign}${x / 1_000_000:.1f}M"
    if x >= 1_000:
        return f"{sign}${x / 1_000:.1f}K"
    return f"{sign}${x:,}"


def _safe_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        n = int(v)
    except (ValueError, TypeError):
        return None
    return n


def _compute_from_cards(cards: list[ReportCard]) -> dict[str, Any]:
    total = len(cards)
    if total == 0:
        return {
            "degrees_cooked": 0,
            "c_or_worse_pct": 0.0,
            "tuition_in_shambles_usd": 0,
            "regret_score_0_5": 0.0,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "display": {
                "degrees_cooked": "0+",
                "c_or_worse_pct": "0%",
                "tuition_in_shambles": "$0",
                "regret_score": "0.0/5",
            },
        }

    c_or_worse = 0
    tuition_in_shambles = 0
    regret_samples: list[float] = []

    for card in cards:
        grade = (card.grade or "").strip().upper()
        if grade in {"C", "D", "F"}:
            c_or_worse += 1

        r = card.research
        gap = _safe_int(r.tuition_opportunity_gap)
        if gap is None and r.estimated_tuition is not None and r.tuition_if_invested is not None:
            gap = int(r.tuition_if_invested - r.estimated_tuition)
        if gap is not None and gap > 0:
            tuition_in_shambles += gap

        cooked = _safe_int(r.overall_cooked_0_100)
        if cooked is None:
            cooked = _safe_int(r.ai_replacement_risk_0_100) or 50
        regret_samples.append(max(0.0, min(5.0, cooked / 20.0)))

    pct = round((c_or_worse / total) * 100, 1)
    regret = round(sum(regret_samples) / len(regret_samples), 1) if regret_samples else 0.0

    return {
        "degrees_cooked": total,
        "c_or_worse_pct": pct,
        "tuition_in_shambles_usd": tuition_in_shambles,
        "regret_score_0_5": regret,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "display": {
            "degrees_cooked": f"{total:,}+",
            "c_or_worse_pct": f"{round(pct)}%",
            "tuition_in_shambles": _format_compact_usd(tuition_in_shambles),
            "regret_score": f"{regret:.1f}/5",
        },
    }


async def _collect_report_cards(store) -> list[ReportCard]:
    cards: list[ReportCard] = []

    if getattr(store, "uses_firestore", False):
        db = get_async_firestore()
        if not db:
            return cards
        async for doc in db.collection(SESSIONS_COLLECTION).stream():
            data = doc.to_dict() or {}
            raw_card = data.get("report_card")
            if not isinstance(raw_card, dict):
                continue
            try:
                cards.append(ReportCard.model_validate(raw_card))
            except Exception:
                continue
        return cards

    memory = getattr(store, "_memory", {})
    for session in memory.values():
        if isinstance(session, Session) and session.report_card:
            cards.append(session.report_card)
    return cards


async def _read_metrics_snapshot() -> dict[str, Any] | None:
    db = get_async_firestore()
    if not db:
        return None
    doc = await db.collection(METRICS_COLLECTION).document(METRICS_DOC_ID).get()
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    if not isinstance(data, dict):
        return None
    return data


async def _write_metrics_snapshot(snapshot: dict[str, Any]) -> None:
    db = get_async_firestore()
    if not db:
        return
    await db.collection(METRICS_COLLECTION).document(METRICS_DOC_ID).set(snapshot)


async def recompute_public_metrics(store) -> dict[str, Any]:
    cards = await _collect_report_cards(store)
    snapshot = _compute_from_cards(cards)
    await _write_metrics_snapshot(snapshot)
    return snapshot


async def get_public_metrics(store) -> dict[str, Any]:
    snap = await _read_metrics_snapshot()
    if isinstance(snap, dict) and "display" in snap:
        return snap
    return await recompute_public_metrics(store)


def _make_fake_session() -> Session:
    degrees = [
        "Business Administration",
        "Psychology",
        "Communications",
        "Computer Science",
        "Economics",
        "Marketing",
        "English",
        "Biology",
        "Political Science",
    ]
    schools = [
        "State University",
        "City College",
        "Northern Tech",
        "Westbridge University",
        "Metro Institute",
        "Kingsford University",
    ]
    jobs = [
        "Marketing Coordinator",
        "Data Analyst",
        "Operations Associate",
        "Junior Developer",
        "Account Manager",
        "HR Specialist",
        "Student",
    ]
    regions = [("United States", "USD"), ("United Kingdom", "GBP"), ("Germany", "EUR")]

    region, cc = random.choice(regions)
    degree = random.choice(degrees)
    school = random.choice(schools)
    job = random.choice(jobs)
    grad_year = random.randint(2012, 2026)
    salary = random.randint(35_000, 140_000) if job != "Student" else None
    years = random.randint(0, 12)

    est_tuition = random.randint(28_000, 160_000)
    invested = int(est_tuition * random.uniform(1.25, 2.8))
    gap = max(0, invested - est_tuition)
    ai = random.randint(38, 95)
    cooked = random.randint(max(40, ai - 8), min(100, ai + 10))

    if cooked >= 80:
        grade, score = "F", random.randint(18, 34)
    elif cooked >= 65:
        grade, score = "D", random.randint(35, 49)
    elif cooked >= 50:
        grade, score = "C", random.randint(50, 64)
    elif cooked >= 35:
        grade, score = "B", random.randint(65, 79)
    else:
        grade, score = "A", random.randint(80, 96)

    profile = UserProfile(
        name=f"User-{uuid.uuid4().hex[:6]}",
        degree=degree,
        university=school,
        graduation_year=grad_year,
        current_job=job,
        current_company="" if job == "Student" else "Sample Co",
        salary=salary,
        years_experience=years,
        country_or_region=region,
        currency_code=cc,
        tuition_paid=est_tuition,
        tuition_is_total=True,
        source="fake_seed",
    )
    research = ResearchData(
        currency_code=cc,
        avg_salary_for_degree=random.randint(42_000, 110_000),
        avg_salary_for_role=random.randint(40_000, 120_000),
        median_salary_for_role=random.randint(38_000, 115_000),
        salary_range_low=random.randint(28_000, 70_000),
        salary_range_high=random.randint(75_000, 185_000),
        estimated_tuition=est_tuition,
        tuition_if_invested=invested,
        tuition_opportunity_gap=gap,
        degree_roi_rank=f"{random.randint(40, 390)}/400",
        job_market_trend=random.choice(["growing", "flat", "shrinking"]),
        unemployment_rate_pct=round(random.uniform(2.1, 8.9), 1),
        job_openings_estimate=random.randint(12_000, 360_000),
        ai_replacement_risk_0_100=ai,
        ai_risk_reasoning="Synthetic seeded data for homepage metrics.",
        overall_cooked_0_100=cooked,
        safeguard_tips=[
            "Own measurable outcomes, not just task execution.",
            "Use AI tools weekly on real deliverables.",
            "Build a visible portfolio of before/after impact.",
        ],
        honest_take="Synthetic seeded report for dashboard metrics.",
    )
    report_card = ReportCard(
        session_id=str(uuid.uuid4()),
        grade=grade,
        grade_score=score,
        profile=profile,
        research=research,
        roast_quote="",
    )
    return Session(
        session_id=report_card.session_id,
        profile=profile,
        research=research,
        report_card=report_card,
        created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 200)),
        voice_activity=[],
    )


def _seed_firestore_sync(count: int) -> int:
    db = get_sync_firestore()
    if not db:
        return 0

    inserted = 0
    batch = db.batch()
    for i in range(count):
        session = _make_fake_session()
        ref = db.collection(SESSIONS_COLLECTION).document(session.session_id)
        batch.set(ref, _session_to_firestore_doc(session))
        inserted += 1
        if (i + 1) % 400 == 0:
            batch.commit()
            batch = db.batch()
    batch.commit()
    return inserted


async def seed_fake_sessions(store, count: int = 200) -> tuple[int, bool]:
    n = max(1, min(5000, int(count)))

    if getattr(store, "uses_firestore", False):
        db = get_async_firestore()
        if not db:
            return (0, False)
        doc_ref = db.collection(METRICS_COLLECTION).document(METRICS_DOC_ID)
        existing = await doc_ref.get()
        data = existing.to_dict() or {}
        if bool(data.get("bootstrap_fake_seed_done")):
            return (0, True)
        seeded = await asyncio.to_thread(_seed_firestore_sync, n)
        await doc_ref.set(
            {
                "bootstrap_fake_seed_done": True,
                "bootstrap_fake_seed_count": seeded,
                "bootstrap_fake_seeded_at": datetime.now(timezone.utc).isoformat(),
            },
            merge=True,
        )
        return (seeded, False)

    memory = getattr(store, "_memory", None)
    if not isinstance(memory, dict):
        return (0, False)
    if bool(getattr(store, "_bootstrap_fake_seed_done", False)):
        return (0, True)
    for _ in range(n):
        s = _make_fake_session()
        memory[s.session_id] = s
    setattr(store, "_bootstrap_fake_seed_done", True)
    return (n, False)
