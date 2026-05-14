"use client";

import { useState } from "react";
import Link from "next/link";
import { Term, Document } from "@/lib/api";

const CATEGORY_COLORS: Record<string, string> = {
  slogan:        "#f97316",
  policy_phrase: "#a78bfa",
  ideological:   "#e85d4a",
  economic:      "#fbbf24",
  diplomatic:    "#34d399",
  technology:    "#4a9eed",
  other:         "#64748b",
};

const TYPE_LABELS: Record<string, string> = {
  five_year_plan:           "Five-Year Plans",
  two_sessions_national:    "Two Sessions",
  economic_work_conference: "Econ Work Conference",
  party_congress:           "Party Congress",
  plenum:                   "Third Plenary Session",
  politburo:                "Politburo",
};

interface Props {
  terms: Term[];
  documents: Document[];
}

export default function TermsPageClient({ terms, documents }: Props) {
  const [activeType, setActiveType]     = useState<string | null>(null);
  const [visibleSet, setVisibleSet]     = useState<Set<string> | null>(null);
  const [loading, setLoading]           = useState(false);

  // Unique doc types present in the loaded documents
  const docTypes = Array.from(
    new Set(documents.map((d) => d.meeting_category).filter(Boolean) as string[])
  );

  async function selectType(type: string) {
    if (activeType === type) {
      setActiveType(null);
      setVisibleSet(null);
      return;
    }
    setActiveType(type);
    setLoading(true);

    const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const docsOfType = documents.filter((d) => d.meeting_category === type);

    const results = await Promise.all(
      docsOfType.map((d) =>
        fetch(`${BASE}/documents/${d.id}/terms`, { cache: "no-store" })
          .then((r) => r.json())
          .then((rows: { term_zh: string }[]) => rows.map((r) => r.term_zh))
          .catch(() => [] as string[])
      )
    );

    setVisibleSet(new Set(results.flat()));
    setLoading(false);
  }

  const visibleTerms = visibleSet
    ? terms.filter((t) => visibleSet.has(t.term_zh))
    : terms;

  const byCategory = visibleTerms.reduce<Record<string, Term[]>>((acc, t) => {
    (acc[t.category] ??= []).push(t);
    return acc;
  }, {});

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold mb-1">Tracked Terms</h1>
        <p style={{ color: "var(--muted)" }} className="text-sm">
          Click any term to see its frequency timeline, context excerpts, and omission gaps.
        </p>
      </div>

      {/* Doc-type filter chips */}
      <div className="flex flex-wrap gap-2 mb-6 items-center">
        <span className="text-xs" style={{ color: "var(--muted)" }}>Filter:</span>
        {docTypes.map((type) => {
          const active = activeType === type;
          return (
            <button
              key={type}
              onClick={() => selectType(type)}
              style={{
                fontSize: "0.75rem",
                padding: "3px 10px",
                borderRadius: 9999,
                border: active ? "1px solid #4a9eed" : "1px solid var(--border)",
                background: active ? "#4a9eed22" : "var(--surface)",
                color: active ? "#4a9eed" : "var(--muted)",
                cursor: "pointer",
                fontWeight: active ? 600 : 400,
              }}
            >
              {loading && active ? "…" : TYPE_LABELS[type] ?? type.replace(/_/g, " ")}
            </button>
          );
        })}
        {activeType && (
          <button
            onClick={() => { setActiveType(null); setVisibleSet(null); }}
            style={{
              fontSize: "0.75rem",
              padding: "3px 10px",
              borderRadius: 9999,
              border: "1px solid var(--border)",
              background: "none",
              color: "var(--muted)",
              cursor: "pointer",
            }}
          >
            ✕ clear
          </button>
        )}
      </div>

      {activeType && !loading && (
        <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>
          {visibleTerms.length} term{visibleTerms.length !== 1 ? "s" : ""} appear in{" "}
          <span style={{ color: "var(--fg)" }}>{TYPE_LABELS[activeType]}</span>
        </p>
      )}

      {Object.entries(byCategory).map(([category, catTerms]) => (
        <section key={category} className="mb-8">
          <div className="flex items-center gap-2 mb-3">
            <span
              className="text-xs font-medium px-2 py-0.5 rounded-full uppercase tracking-wider"
              style={{ background: CATEGORY_COLORS[category] + "22", color: CATEGORY_COLORS[category] }}
            >
              {category.replace("_", " ")}
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {catTerms.map((term) => (
              <Link
                key={term.id}
                href={`/terms/${term.id}`}
                className="block rounded-lg p-4 hover:opacity-90"
                style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
              >
                <div className="text-xl font-medium mb-0.5">{term.term_zh}</div>
                <div className="text-sm mb-2" style={{ color: "var(--muted)" }}>
                  {term.term_en ?? "—"}
                </div>
                {term.first_seen_date && (
                  <div className="text-xs" style={{ color: CATEGORY_COLORS[category] }}>
                    First seen {term.first_seen_date}
                  </div>
                )}
              </Link>
            ))}
          </div>
        </section>
      ))}

      {visibleTerms.length === 0 && !loading && (
        <p className="text-sm text-center py-12" style={{ color: "var(--muted)" }}>
          No tracked terms appear in {TYPE_LABELS[activeType!] ?? activeType} documents.
        </p>
      )}
    </div>
  );
}
