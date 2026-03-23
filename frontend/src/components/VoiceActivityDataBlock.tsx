"use client";

import type { VoiceActivityRow } from "./VoiceActivityPanel";

function asStringArray(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is string => typeof x === "string");
}

function asNumberArray(v: unknown): number[] {
  if (!Array.isArray(v)) return [];
  return v.map((x) => (typeof x === "number" ? x : Number(x))).filter((n) => !Number.isNaN(n));
}

const KEY_LABELS: Record<string, string> = {
  avg_salary_for_degree: "Typical salary (your field)",
  avg_salary_for_role: "Typical salary (your role)",
  median_salary_for_role: "Median salary (your role)",
  estimated_tuition: "Estimated tuition",
  tuition_if_invested: "If that tuition was invested instead",
  ai_replacement_risk_0_100: "Automation / AI risk",
  overall_cooked_0_100: "Overall “how cooked” meter",
  job_market_trend: "Job market direction",
};

function formatMoney(n: number, currencyCode: string): string {
  const code = (currencyCode || "USD").trim().toUpperCase() || "USD";
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: code,
      maximumFractionDigits: 0,
    }).format(n);
  } catch {
    return `${code} ${n.toLocaleString()}`;
  }
}

function formatKeyValue(key: string, v: unknown, currencyCode: string): string {
  if (v == null || v === "") return "—";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (typeof v === "string") return v;
  if (typeof v !== "number" || Number.isNaN(v)) return String(v);

  if (key === "ai_replacement_risk_0_100" || key === "overall_cooked_0_100") {
    return `${Math.round(v)} / 100`;
  }
  if (
    key === "avg_salary_for_degree" ||
    key === "avg_salary_for_role" ||
    key === "median_salary_for_role" ||
    key === "estimated_tuition" ||
    key === "tuition_if_invested"
  ) {
    return formatMoney(v, currencyCode);
  }
  return v.toLocaleString();
}

/** Friendly breakdown of webhook research payloads for the live feed. */
export default function VoiceActivityDataBlock({ row }: { row: VoiceActivityRow }) {
  const d = row.data;
  if (!d || typeof d !== "object") return null;

  const queries = asStringArray((d as Record<string, unknown>).queries);
  const hits = asNumberArray((d as Record<string, unknown>).hits_per_query);
  const step = (d as Record<string, unknown>).step;
  const currencyCode =
    typeof (d as Record<string, unknown>).currency_code === "string"
      ? ((d as Record<string, unknown>).currency_code as string)
      : "USD";

  if (queries.length === 0 && step !== "research_complete") return null;

  const maxList = 6;
  const shown = queries.slice(0, maxList);
  const rest = queries.length - shown.length;
  const queryCount = typeof (d as { query_count?: number }).query_count === "number"
    ? (d as { query_count: number }).query_count
    : queries.length;

  return (
    <div className="mt-2 pt-2 border-t border-white/5 space-y-2.5 text-[11px] text-[var(--subtle)] leading-snug">
      {step === "research_started" && (
        <p className="text-[var(--subtle)]/90 font-light">
          {(d as { note?: string }).note ||
            "We’re gathering public info so Donald’s roast is based on real numbers."}
        </p>
      )}

      {queries.length > 0 && step === "research_started" && (
        <div>
          <p className="text-[10px] font-semibold text-[var(--fg)]/80 uppercase tracking-wider mb-1.5">
            Sample lookups ({queryCount})
          </p>
          <ul className="space-y-1 pl-0.5">
            {shown.map((q, i) => (
              <li key={i} className="flex gap-2 break-words">
                <span className="text-[var(--gold)]/70 shrink-0">·</span>
                <span>{q}</span>
              </li>
            ))}
          </ul>
          {rest > 0 ? (
            <p className="text-[10px] text-[var(--subtle)]/60 mt-1.5">…and {rest} more checks</p>
          ) : null}
        </div>
      )}

      {step === "research_complete" && queries.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-[var(--fg)]/80 uppercase tracking-wider mb-1.5">
            Topics we checked
          </p>
          <ul className="space-y-1 pl-0.5">
            {shown.map((q, i) => (
              <li key={i} className="flex gap-2 break-words">
                <span className="text-[var(--gold)]/70 shrink-0">·</span>
                <span>{q}</span>
                {hits[i] !== undefined ? (
                  <span className="text-[var(--subtle)]/45 shrink-0 whitespace-nowrap">
                    · {hits[i]} results
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
          {rest > 0 ? <p className="text-[10px] text-[var(--subtle)]/60 mt-1.5">…and {rest} more</p> : null}
        </div>
      )}

      {step === "research_complete" && (
        <>
          {(d as { total_snippet_hits?: number }).total_snippet_hits != null ? (
            <p className="text-[var(--subtle)]/85 font-light">
              Pulled useful text from{" "}
              <span className="text-[var(--fg)]/90 font-medium">
                {(d as { total_snippet_hits: number }).total_snippet_hits.toLocaleString()}
              </span>{" "}
              search results to build your snapshot.
            </p>
          ) : null}

          {(d as { key_numbers?: Record<string, unknown> }).key_numbers &&
          typeof (d as { key_numbers: Record<string, unknown> }).key_numbers === "object" ? (
            <div>
              <p className="text-[10px] font-semibold text-[var(--fg)]/80 uppercase tracking-wider mb-1.5">
                At a glance
              </p>
              <ul className="space-y-1.5">
                {Object.entries((d as { key_numbers: Record<string, unknown> }).key_numbers)
                  .filter(([, v]) => v != null && v !== "")
                  .slice(0, 10)
                  .map(([k, v]) => (
                    <li key={k} className="flex flex-col gap-0.5 sm:flex-row sm:items-baseline sm:gap-2">
                      <span className="text-[var(--subtle)]/80 shrink-0">
                        {KEY_LABELS[k] || k.replace(/_/g, " ")}
                      </span>
                      <span className="text-[var(--fg)]/90 font-medium tabular-nums">
                        {formatKeyValue(k, v, currencyCode)}
                      </span>
                    </li>
                  ))}
              </ul>
            </div>
          ) : null}

          {(d as { sources?: { title?: string; url?: string }[] }).sources &&
          ((d as { sources: unknown[] }).sources?.length ?? 0) > 0 ? (
            <div>
              <p className="text-[10px] font-semibold text-[var(--fg)]/80 uppercase tracking-wider mb-1.5">
                Sources worth opening
              </p>
              <ul className="space-y-1.5">
                {((d as { sources: { title?: string; url?: string }[] }).sources || []).slice(0, 6).map((s, i) => (
                  <li key={i} className="break-words">
                    {s.url ? (
                      <a
                        href={s.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[var(--gold)]/90 hover:underline"
                      >
                        {s.title || "View source"}
                      </a>
                    ) : (
                      <span>{s.title || "Source"}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {(d as { named_sources?: string[] }).named_sources &&
          ((d as { named_sources: string[] }).named_sources?.length ?? 0) > 0 ? (
            <p className="text-[10px] text-[var(--subtle)]/80">
              <span className="font-semibold text-[var(--subtle)]">Also cited: </span>
              {(d as { named_sources: string[] }).named_sources.join(" · ")}
            </p>
          ) : null}
        </>
      )}
    </div>
  );
}
