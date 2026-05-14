import { api } from "@/lib/api";

const SIGNAL_META: Record<string, { label: string; bg: string; text: string; desc: string }> = {
  DEBUT:  { label: "DEBUT",  bg: "#a78bfa22", text: "#a78bfa", desc: "Never appeared before in any document" },
  SPIKE:  { label: "SPIKE",  bg: "#fbbf2422", text: "#fbbf24", desc: "Frequency ≥ 4× its historical average" },
  RETURN: { label: "RETURN", bg: "#34d39922", text: "#34d399", desc: "Absent for 2+ prior meetings, now back" },
  CLAUDE: { label: "CLAUDE", bg: "#4a9eed22", text: "#4a9eed", desc: "Flagged by AI as politically significant" },
};

const CATEGORY_COLORS: Record<string, string> = {
  slogan:        "#f97316",
  policy_phrase: "#a78bfa",
  ideological:   "#e85d4a",
  economic:      "#fbbf24",
  diplomatic:    "#34d399",
  technology:    "#4a9eed",
  other:         "#64748b",
};

export default async function CandidatesPage() {
  const candidates = await api.candidates();

  const bySignal = candidates.reduce<Record<string, typeof candidates>>((acc, c) => {
    (acc[c.signal] ??= []).push(c);
    return acc;
  }, {});

  const signalOrder = ["DEBUT", "SPIKE", "RETURN", "CLAUDE"];

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold mb-1">Signal Candidates</h1>
        <p style={{ color: "var(--muted)" }} className="text-sm max-w-2xl">
          Phrases automatically detected by the statistical and AI pipeline — not in the tracked terms list yet.
          These are words whose frequency, position, or framing shifted in a way that may be politically significant.
        </p>
      </div>

      {candidates.length === 0 && (
        <div className="rounded-lg p-8 text-center"
             style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <p style={{ color: "var(--muted)" }} className="text-sm mb-2">No candidates yet.</p>
          <p style={{ color: "var(--muted)" }} className="text-xs">
            Run <code className="px-1 py-0.5 rounded" style={{ background: "#0f1117" }}>
              python scripts/ingest_econconf.py
            </code> then{" "}
            <code className="px-1 py-0.5 rounded" style={{ background: "#0f1117" }}>
              python scripts/analyze_document.py --all --no-claude
            </code> to populate this list.
          </p>
        </div>
      )}

      {signalOrder.filter((s) => bySignal[s]?.length).map((signal) => {
        const meta = SIGNAL_META[signal] ?? SIGNAL_META.CLAUDE;
        const group = bySignal[signal];
        return (
          <section key={signal} className="mb-8">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-xs font-medium px-2 py-0.5 rounded-full"
                    style={{ background: meta.bg, color: meta.text }}>
                {meta.label}
              </span>
              <span className="text-sm" style={{ color: "var(--muted)" }}>{meta.desc}</span>
              <span className="ml-auto text-xs" style={{ color: "var(--muted)" }}>{group.length}</span>
            </div>

            <div className="rounded-lg overflow-hidden"
                 style={{ border: "1px solid var(--border)" }}>
              {group.map((c, i) => {
                const catColor = CATEGORY_COLORS[c.category] ?? "#64748b";
                return (
                  <div key={c.id}
                       className="px-4 py-3 flex items-start gap-4"
                       style={{
                         background: "var(--surface)",
                         borderBottom: i < group.length - 1 ? "1px solid var(--border)" : "none",
                       }}>
                    {/* Term */}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                        <span className="text-lg font-medium">{c.term_zh}</span>
                        {c.term_en && (
                          <span className="text-sm" style={{ color: "var(--muted)" }}>{c.term_en}</span>
                        )}
                        {c.category && c.category !== "other" && (
                          <span className="text-xs px-1.5 py-0.5 rounded"
                                style={{ background: catColor + "22", color: catColor }}>
                            {c.category.replace("_", " ")}
                          </span>
                        )}
                      </div>
                      {c.significance && (
                        <p className="text-xs mb-1" style={{ color: "var(--muted)" }}>{c.significance}</p>
                      )}
                      {c.context && (
                        <p className="text-xs font-mono rounded px-2 py-1 mt-1"
                           style={{ background: "#0f1117", color: "#94a3b8" }}>
                          …{c.context}…
                        </p>
                      )}
                    </div>

                    {/* Stats */}
                    <div className="shrink-0 text-right text-xs" style={{ color: "var(--muted)" }}>
                      {c.frequency != null && (
                        <div>
                          <span className="text-sm font-medium" style={{ color: "var(--text)" }}>
                            ×{c.frequency}
                          </span>
                          {" "}this doc
                        </div>
                      )}
                      {c.prior_avg != null && c.prior_avg > 0 && (
                        <div>avg {c.prior_avg.toFixed(1)} prior</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}
