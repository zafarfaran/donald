const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DEMO_MODE = !process.env.NEXT_PUBLIC_API_URL;

// ── Mock data for demo mode (no backend needed) ──

function mockSessionId() {
  return "demo-" + Math.random().toString(36).slice(2, 10);
}

const MOCK_REPORT_CARD = {
  session_id: "demo",
  grade: "D",
  grade_score: 38,
  profile: {
    name: "Demo User",
    degree: "Communications",
    university: "State University",
    graduation_year: 2021,
    current_job: "Marketing Coordinator",
    salary: 48000,
    years_experience: 3,
    country_or_region: "United States",
    currency_code: "USD",
  },
  research: {
    currency_code: "USD",
    avg_salary_for_degree: 52000,
    estimated_tuition: 95000,
    tuition_if_invested: 142000,
    tuition_opportunity_gap: 47000,
    degree_roi_rank: "312/400",
    job_market_trend: "shrinking",
    ai_replacement_risk_0_100: 72,
    overall_cooked_0_100: 68,
    ai_risk_reasoning: "72% of marketing coordinator tasks — content drafting, reporting, campaign scheduling — overlap with what current LLMs and automation tools handle. 3 years of experience isn't deep enough specialization to offset that.",
    safeguard_tips: [
      "Own campaign outcomes (revenue, pipeline) not just the slide decks and calendar posts.",
      "Pick one AI workflow you actually ship with weekly — prompts, evals, review — so you become the person who automates the work, not the one replaced by it.",
      "Quarterly task audit: list what you do monthly and tag each as automate / augment / human-only.",
      "Build a public portfolio of before/after results where AI sped you up — proof you multiply output.",
    ],
    honest_take: "You paid $95k for comms; market averages for coordinators sit around $52k while that tuition could've compounded to ~$142k in the S&P. With ~72% task overlap with AI, own revenue outcomes—not slide decks.",
    methodology_note:
      "Numbers come from the pages linked below. AI condensed snippets into this card. S&P-style growth uses a long-run average when snippets had no clear rate.",
    named_sources: ["BLS", "Glassdoor", "Payscale"],
    sources: [
      { title: "Marketing specialists — Occupational Outlook", url: "https://www.bls.gov/ooh/", topic: "Marketing Coordinator average salary median salary 2026 BLS" },
      { title: "Marketing coordinator salary range", url: "https://www.glassdoor.com/", topic: "Marketing Coordinator salary range entry level senior 2026" },
    ],
  },
  roast_quote: "",
};

// ── API functions (with demo fallback) ──

export async function createSession(profile: {
  name: string;
  degree: string;
  university: string;
  graduation_year: number;
  current_job: string;
  current_company?: string;
  salary?: number;
  years_experience?: number;
  source?: string;
}): Promise<{ session_id: string }> {
  if (DEMO_MODE) {
    await new Promise((r) => setTimeout(r, 400));
    return { session_id: mockSessionId() };
  }
  const res = await fetch(`${API_URL}/api/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
  return res.json();
}

/** Empty session for voice: profile is not accumulated server-side; agent passes inline \`profile\` to \`research_degree\`. */
export function createVoiceSession(): Promise<{ session_id: string }> {
  return createSession({
    name: "",
    degree: "",
    university: "",
    graduation_year: 0,
    current_job: "",
    current_company: "",
    source: "voice",
  });
}

export async function scrapeLinkedIn(
  linkedin_url: string
): Promise<{
  success: boolean;
  name?: string;
  degree?: string;
  university?: string;
  graduation_year?: number;
  current_job?: string;
  error?: string;
}> {
  if (DEMO_MODE) {
    await new Promise((r) => setTimeout(r, 800));
    return { success: false, error: "demo mode" };
  }
  const res = await fetch(`${API_URL}/api/scrape`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ linkedin_url }),
  });
  return res.json();
}

export async function getReportCard(sessionId: string) {
  if (DEMO_MODE) {
    await new Promise((r) => setTimeout(r, 500));
    return { ...MOCK_REPORT_CARD, session_id: sessionId };
  }
  const res = await fetch(`${API_URL}/api/report-card/${sessionId}`, {
    cache: "no-store",
  });
  if (!res.ok) return null;
  const data = await res.json();
  return data.report_card;
}

export type VoiceActivityServerItem = {
  id: string;
  ts: string;
  event: string;
  title: string;
  detail: string;
  data?: Record<string, unknown> | null;
};

export type VoiceActivityPollResult = {
  ok: boolean;
  items: VoiceActivityServerItem[];
  error?: string;
  httpStatus?: number;
};

/** Poll while on voice call — webhook + pipeline steps from the API */
export async function fetchVoiceActivity(sessionId: string): Promise<VoiceActivityPollResult> {
  if (DEMO_MODE) return { ok: true, items: [] };
  try {
    const res = await fetch(`${API_URL}/api/session/${sessionId}/voice-activity`, { cache: "no-store" });
    let data: { items?: VoiceActivityServerItem[]; detail?: string } = {};
    try {
      data = await res.json();
    } catch {
      /* empty body */
    }
    if (!res.ok) {
      return {
        ok: false,
        items: [],
        error: typeof data.detail === "string" ? data.detail : res.statusText || `HTTP ${res.status}`,
        httpStatus: res.status,
      };
    }
    return { ok: true, items: Array.isArray(data.items) ? data.items : [] };
  } catch (e) {
    return {
      ok: false,
      items: [],
      error: e instanceof Error ? e.message : "Cannot reach API (is the backend running?)",
    };
  }
}

/** Browser → \`get_user_profile\` webhook (LinkedIn/manual sessions with stored profile). Voice flow does not use this. */
export async function webhookGetUserProfile(sessionId: string): Promise<{ ok: boolean; error?: string }> {
  if (DEMO_MODE) return { ok: true };
  try {
    const res = await fetch(`${API_URL}/api/webhooks/get_user_profile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    if (!res.ok) {
      const t = await res.text();
      return { ok: false, error: t.slice(0, 200) || `HTTP ${res.status}` };
    }
    return { ok: true };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Network error" };
  }
}
