import Link from "next/link";
import { api, Term } from "@/lib/api";
import CustomTermSearch from "@/components/CustomTermSearch";

const CATEGORY_COLORS: Record<string, string> = {
  ideological:   "#e85d4a",
  macroeconomic: "#fbbf24",
  industrial:    "#ec4899",
  livelihood:    "#f97316",
  environmental: "#22c55e",
  diplomatic:    "#a78bfa",
  technology:    "#4a9eed",
  other:         "#64748b",
};

const CATEGORY_LABELS: Record<string, string> = {
  ideological:   "Ideological",
  macroeconomic: "Macroeconomic",
  industrial:    "Industrial",
  livelihood:    "Livelihood",
  environmental: "Environmental",
  diplomatic:    "Diplomatic",
  technology:    "Technology",
  other:         "Other",
};

export default async function HomePage() {
  const terms = await api.terms();

  const byCategory = terms.reduce<Record<string, Term[]>>((acc, t) => {
    (acc[t.category] ??= []).push(t);
    return acc;
  }, {});

  for (const cat of Object.keys(byCategory)) {
    byCategory[cat].sort((a, b) => (b.first_year ?? 0) - (a.first_year ?? 0));
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold mb-1">Tracked Terms</h1>
        <p style={{ color: "var(--muted)" }} className="text-sm">
          Click any term to see its frequency timeline, context excerpts, and omission gaps.
        </p>
      </div>

      {(["ideological", "macroeconomic", "industrial", "environmental", "technology", "livelihood", "diplomatic", "other"])
    .filter((cat) => byCategory[cat]?.length)
    .map((category) => [category, byCategory[category]] as [string, Term[]])
    .map(([category, catTerms]) => (
        <section key={category} className="mb-8">
          <div className="flex items-center gap-2 mb-3">
            <span
              className="text-xs font-medium px-2 py-0.5 rounded-full uppercase tracking-wider"
              style={{ background: CATEGORY_COLORS[category] + "22", color: CATEGORY_COLORS[category] }}
            >
              {CATEGORY_LABELS[category] ?? category}
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {catTerms.map((term) => (
              <Link
                key={term.id}
                href={`/terms/${term.id}`}
                className="block rounded-lg p-4 transition-colors hover:opacity-90"
                style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
              >
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xl font-medium">{term.term_zh}</span>
                  {term.first_year && term.first_year >= new Date().getFullYear() - 4 && (
                    <span className="text-xs font-medium px-1.5 py-0.5 rounded"
                          style={{ background: CATEGORY_COLORS[category] + "33", color: CATEGORY_COLORS[category] }}>
                      new
                    </span>
                  )}
                </div>
                <div className="text-sm mb-2" style={{ color: "var(--muted)" }}>
                  {term.term_en ?? "—"}
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span style={{ color: CATEGORY_COLORS[category] }}>
                    {term.first_year
                      ? term.first_year === term.last_year
                        ? term.first_year
                        : `${term.first_year}–${term.last_year}`
                      : ""}
                  </span>
                  <span style={{ color: "var(--muted)" }}>
                    {term.total_mentions} mention{term.total_mentions !== 1 ? "s" : ""}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      ))}

      <CustomTermSearch />
    </div>
  );
}
