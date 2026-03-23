from backend.models import ResearchData


def _career_quality_0_100(research: ResearchData, salary: int | None) -> int:
    """Legacy factors: salary vs degree benchmark, ROI-ish, job trend, tuition vs invested."""
    factors: list[tuple[float, float]] = []

    effective_salary = salary or research.avg_salary_for_degree

    if effective_salary and research.avg_salary_for_degree:
        ratio = effective_salary / research.avg_salary_for_degree
        score = min(max((ratio - 0.5) / 1.0, 0.0), 1.0)
        factors.append((0.3, score))

    if effective_salary and research.estimated_tuition:
        ten_year_earnings = effective_salary * 10
        roi = (ten_year_earnings - research.estimated_tuition) / research.estimated_tuition
        score = min(max((roi - 0) / 10, 0.0), 1.0)
        factors.append((0.3, score))

    if research.job_market_trend:
        trend_scores = {"growing": 0.9, "flat": 0.5, "shrinking": 0.15}
        score = trend_scores.get(research.job_market_trend, 0.5)
        factors.append((0.2, score))

    if research.estimated_tuition and research.tuition_if_invested:
        gap_ratio = research.tuition_if_invested / research.estimated_tuition
        score = min(max(1.0 - (gap_ratio - 1.0) / 4.0, 0.0), 1.0)
        factors.append((0.2, score))

    if not factors:
        return 50

    total_weight = sum(w for w, _ in factors)
    weighted = sum(w * s for w, s in factors) / total_weight
    return int(min(max(weighted * 100, 0), 100))


def compute_grade(
    research: ResearchData,
    salary: int | None = None,
    years_experience: int | None = None,
) -> tuple[str, int]:
    """
    Letter grade + 0–100 score.
    Blends career/tuition signals with AI replacement risk (high risk drags grade down).
    """
    career = _career_quality_0_100(research, salary)
    ai = research.ai_replacement_risk_0_100
    if ai is None:
        ai = 50

    # Survival score: career matters, but AI risk pulls you down meaningfully
    survival = int(0.5 * career + 0.5 * (100 - ai))

    if years_experience is not None and years_experience >= 10:
        survival = min(100, survival + 4)
    elif years_experience is not None and years_experience <= 1:
        survival = max(0, survival - 3)

    # Strict: high AI replacement risk caps how good the letter grade can look
    if ai > 70:
        cap = int(72 - (ai - 70) * 1.15)
        cap = max(28, min(68, cap))
        survival = min(survival, cap)

    grade_score = min(max(survival, 0), 100)

    if grade_score >= 80:
        grade = "A"
    elif grade_score >= 65:
        grade = "B"
    elif grade_score >= 50:
        grade = "C"
    elif grade_score >= 35:
        grade = "D"
    else:
        grade = "F"

    return (grade, grade_score)
