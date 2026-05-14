import { api } from "@/lib/api";
import TermPageClient from "@/components/TermPageClient";
import Link from "next/link";

const CATEGORY_COLORS: Record<string, string> = {
  slogan:        "#f97316",
  policy_phrase: "#a78bfa",
  ideological:   "#e85d4a",
  economic:      "#fbbf24",
  diplomatic:    "#34d399",
  technology:    "#4a9eed",
  other:         "#64748b",
};

export default async function TermPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const termId = Number(id);

  const [terms, freq, rankings, cachedFraming] = await Promise.all([
    api.terms(),
    api.frequency(termId),
    api.rankings(termId),
    api.framing(termId),
  ]);

  const term = terms.find((t) => t.id === termId);
  if (!term) return <div>Term not found</div>;

  const color = CATEGORY_COLORS[term.category] ?? "#e85d4a";

  const activeFreq = freq.filter((p) => p.frequency > 0);
  const firstYear  = activeFreq.length ? activeFreq[0].meeting_date.slice(0, 4) : null;
  const lastYear   = activeFreq.length ? activeFreq[activeFreq.length - 1].meeting_date.slice(0, 4) : null;
  const yearRange  = firstYear === lastYear ? firstYear : firstYear && lastYear ? `${firstYear}–${lastYear}` : null;

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link href="/" style={{ color: "var(--muted)" }} className="text-sm hover:text-white mb-3 inline-block">
          ← All terms
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold mb-1">{term.term_zh}</h1>
            <p style={{ color: "var(--muted)" }}>{term.term_en}</p>
          </div>
          <span
            className="text-xs font-medium px-2 py-1 rounded-full uppercase tracking-wider shrink-0 mt-1"
            style={{ background: color + "22", color }}
          >
            {term.category.replace("_", " ")}
          </span>
        </div>
        {yearRange && (
          <p className="mt-2 text-sm" style={{ color }}>{yearRange}</p>
        )}
      </div>

      <TermPageClient
        term={{ term_zh: term.term_zh, term_en: term.term_en ?? null }}
        color={color}
        freq={freq}
        rankings={rankings}
        cachedFraming={cachedFraming}
      />
    </div>
  );
}
