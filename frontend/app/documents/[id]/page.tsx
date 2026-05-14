import { api } from "@/lib/api";
import DocumentPageClient from "@/components/DocumentPageClient";
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

const TYPE_LABELS: Record<string, string> = {
  economic_work_conference: "Economic Work Conference",
  five_year_plan:           "Five-Year Plan",
  two_sessions_national:    "Two Sessions",
  party_congress:           "Party Congress",
  plenum:                   "Third Plenary Session",
  politburo:                "Politburo",
};

export default async function DocumentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const docId = Number(id);

  const [doc, docTerms] = await Promise.all([
    api.document(docId),
    api.documentTerms(docId),
  ]);

  const termColors = Object.fromEntries(
    docTerms.map((t) => [t.term_zh, CATEGORY_COLORS[t.category] ?? "#64748b"])
  );

  const typeLabel = doc.meeting_category ? (TYPE_LABELS[doc.meeting_category] ?? doc.meeting_type ?? "") : (doc.meeting_type ?? "");

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <Link href="/documents" style={{ color: "var(--muted)" }} className="text-sm hover:text-white mb-3 inline-block">
          ← All documents
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold mb-1">{doc.title_zh}</h1>
            {doc.title_en && <p style={{ color: "var(--muted)" }} className="text-sm">{doc.title_en}</p>}
          </div>
          <div className="flex flex-col items-end gap-1 shrink-0 mt-1">
            <span className="text-xs px-2 py-0.5 rounded-full"
                  style={{ background: "#64748b22", color: "#64748b" }}>
              {typeLabel}
            </span>
            <span className="text-xs" style={{ color: "var(--muted)" }}>{doc.meeting_date}</span>
          </div>
        </div>

      </div>

      <DocumentPageClient
        text={doc.raw_text_zh}
        terms={docTerms}
        allTermColors={termColors}
      />
    </div>
  );
}
