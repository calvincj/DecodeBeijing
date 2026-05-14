import { api } from "@/lib/api";
import Link from "next/link";
import TermPageClient from "@/components/TermPageClient";
import { redirect } from "next/navigation";

export default async function CustomTermPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  if (!q) redirect("/");

  const freq = await api.searchFrequency(q);

  const totalMentions = freq.reduce((s, p) => s + p.frequency, 0);

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <Link href="/" style={{ color: "var(--muted)" }} className="text-sm hover:text-white mb-3 inline-block">
          ← All terms
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold mb-1">{q}</h1>
            <p style={{ color: "var(--muted)" }}>Custom search — not a tracked term</p>
          </div>
          <span
            className="text-xs font-medium px-2 py-1 rounded-full uppercase tracking-wider shrink-0 mt-1"
            style={{ background: "#64748b22", color: "#64748b" }}
          >
            custom
          </span>
        </div>
      </div>

      {totalMentions === 0 ? (
        <p className="text-sm py-12 text-center" style={{ color: "var(--muted)" }}>
          "{q}" not found in any document.
        </p>
      ) : (
        <TermPageClient
          term={{ term_zh: q, term_en: null }}
          color="#64748b"
          freq={freq}
          rankings={[]}
          cachedFraming={[]}
        />
      )}
    </div>
  );
}
