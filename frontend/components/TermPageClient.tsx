"use client";

import { useState, useRef, useEffect } from "react";
import FrequencyChart from "@/components/FrequencyChart";
import RankingChart from "@/components/RankingChart";
import FramingPanel from "@/components/FramingPanel";
import { FrequencyPoint, FramingPoint, RankingPoint } from "@/lib/api";

const TYPE_LABELS: Record<string, string> = {
  five_year_plan:           "Five-Year Plans",
  two_sessions_national:    "Two Sessions",
  economic_work_conference: "Econ Work Conference",
  party_congress:           "Party Congress",
  plenum:                   "Third Plenary Session",
  politburo:                "Politburo",
};

interface Props {
  term: { term_zh: string; term_en: string | null };
  color: string;
  freq: FrequencyPoint[];
  rankings: RankingPoint[];
  cachedFraming: FramingPoint[];
}

export default function TermPageClient({ term, color, freq, rankings, cachedFraming }: Props) {
  const docTypes = Array.from(
    new Set(freq.map((p) => p.meeting_category).filter(Boolean) as string[])
  );

  const [selected, setSelected] = useState<Set<string>>(() => new Set(docTypes));
  const [open, setOpen]         = useState(false);
  const dropdownRef             = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  function toggle(type: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(type) ? next.delete(type) : next.add(type);
      return next;
    });
  }

  const allSelected = selected.size === docTypes.length;

  const filteredFreq = freq.filter(
    (p) => p.meeting_category && selected.has(p.meeting_category)
  );
  const filteredFraming = cachedFraming.filter((f) => {
    const fp = freq.find((p) => p.document_id === f.document_id);
    return fp?.meeting_category && selected.has(fp.meeting_category);
  });
  const filteredRankings = rankings.filter((r) => {
    const fp = freq.find((p) => p.document_id === r.document_id);
    return fp?.meeting_category && selected.has(fp.meeting_category);
  });

  const totalMentions = filteredFreq.reduce((s, p) => s + p.frequency, 0);
  const docsPresent   = filteredFreq.filter((p) => p.frequency > 0).length;
  const rankingYears  = new Set(filteredRankings.map((r) => new Date(r.meeting_date).getFullYear()));
  const showRankings  = rankingYears.size >= 2;

  return (
    <>
      {/* Conference selector */}
      <div ref={dropdownRef} style={{ position: "relative", display: "inline-block" }} className="mb-6">
        <button
          onClick={() => setOpen((o) => !o)}
          style={{
            fontSize: "0.75rem",
            padding: "4px 12px",
            borderRadius: 9999,
            border: `1px solid ${!allSelected ? color : "var(--border)"}`,
            background: !allSelected ? color + "22" : "var(--surface)",
            color: !allSelected ? color : "var(--muted)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          Select Conferences
          {!allSelected && <span style={{ fontWeight: 700 }}>{selected.size}/{docTypes.length}</span>}
          <span style={{ opacity: 0.6 }}>▾</span>
        </button>

        {open && (
          <div style={{
            position: "absolute",
            top: "calc(100% + 6px)",
            left: 0,
            minWidth: 200,
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            zIndex: 50,
            overflow: "hidden",
          }}>
            {docTypes.map((type) => {
              const checked = selected.has(type);
              return (
                <button
                  key={type}
                  onClick={() => toggle(type)}
                  style={{
                    width: "100%",
                    textAlign: "left",
                    padding: "8px 12px",
                    fontSize: "0.75rem",
                    background: checked ? color + "11" : "transparent",
                    color: "var(--fg)",
                    cursor: "pointer",
                    border: "none",
                    borderBottom: "1px solid var(--border)",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <span style={{
                    width: 14,
                    height: 14,
                    borderRadius: 3,
                    border: `1.5px solid ${checked ? color : "var(--muted)"}`,
                    background: checked ? color : "transparent",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    fontSize: 9,
                    color: "#000",
                  }}>
                    {checked && "✓"}
                  </span>
                  {TYPE_LABELS[type] ?? type.replace(/_/g, " ")}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 mb-6">
        {[
          { label: "Total mentions", value: totalMentions },
          { label: "Documents present", value: docsPresent },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-lg p-4 text-center"
               style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
            <div className="text-2xl font-semibold">{value}</div>
            <div className="text-xs mt-1" style={{ color: "var(--muted)" }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Frequency */}
      <div className="rounded-lg p-4 mb-6"
           style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        <h2 className="text-sm font-medium mb-4" style={{ color: "var(--muted)" }}>FREQUENCY OVER TIME</h2>
        {filteredFreq.length > 0
          ? <FrequencyChart data={filteredFreq} color={color} />
          : <p style={{ color: "var(--muted)" }} className="text-sm py-8 text-center">No data for selected conferences</p>
        }
      </div>

      {/* AI Framing */}
      <div className="rounded-lg p-4 mb-6"
           style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        <h2 className="text-sm font-medium mb-1" style={{ color: "var(--muted)" }}>GOVERNMENT FRAMING</h2>
        <FramingPanel freq={filteredFreq} termZh={term.term_zh} cachedFraming={filteredFraming} />
      </div>

      {/* Policy task priority */}
      {showRankings && (
        <div className="rounded-lg p-4 mb-6"
             style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <h2 className="text-sm font-medium mb-1" style={{ color: "var(--muted)" }}>POLICY TASK PRIORITY</h2>
          <RankingChart data={filteredRankings} color={color} />
        </div>
      )}

    </>
  );
}
