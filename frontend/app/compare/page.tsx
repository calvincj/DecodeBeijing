import { api } from "@/lib/api";
import CompareSelector from "@/components/CompareSelector";
import CompareChart from "@/components/CompareChart";

interface Props {
  searchParams: Promise<{ a?: string; b?: string }>;
}

export default async function ComparePage({ searchParams }: Props) {
  const { a, b } = await searchParams;
  const terms = await api.terms();

  const termA = a ? Number(a) : terms[0]?.id;
  const termB = b ? Number(b) : terms[1]?.id;

  const compareData = termA && termB ? await api.compare(termA, termB) : null;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold mb-1">Compare Terms</h1>
        <p style={{ color: "var(--muted)" }} className="text-sm">
          Overlay two terms on the same chart to see how their prominence shifts relative to each other.
        </p>
      </div>

      <div className="rounded-lg p-4 mb-6"
           style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        <CompareSelector terms={terms} defaultA={termA} defaultB={termB} />

        {compareData ? (
          <>
            <div className="flex gap-6 mb-4 text-sm">
              <span style={{ color: "#e85d4a" }}>● {compareData.term_a.term_zh}</span>
              <span style={{ color: "#4a9eed" }}>● {compareData.term_b.term_zh}</span>
            </div>
            <CompareChart data={compareData} />
          </>
        ) : (
          <p style={{ color: "var(--muted)" }} className="text-sm py-8 text-center">
            Select two terms above and click Compare.
          </p>
        )}
      </div>

      {compareData && (
        <div className="rounded-lg p-4"
             style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <h2 className="text-sm font-medium mb-4" style={{ color: "var(--muted)" }}>
            RAW DATA
          </h2>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ color: "var(--muted)", borderBottom: "1px solid var(--border)" }}>
                <th className="text-left pb-2">Document</th>
                <th className="text-left pb-2">Date</th>
                <th className="text-right pb-2" style={{ color: "#e85d4a" }}>
                  {compareData.term_a.term_zh}
                </th>
                <th className="text-right pb-2" style={{ color: "#4a9eed" }}>
                  {compareData.term_b.term_zh}
                </th>
              </tr>
            </thead>
            <tbody>
              {[...compareData.series]
                .sort((x, y) => x.meeting_date.localeCompare(y.meeting_date))
                .map((row) => (
                  <tr key={row.document_id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td className="py-2 pr-4">{row.title_zh}</td>
                    <td className="py-2 pr-4" style={{ color: "var(--muted)" }}>{row.meeting_date}</td>
                    <td className="py-2 text-right" style={{ color: row.freq_a > 0 ? "#e85d4a" : "var(--muted)" }}>
                      {row.freq_a}
                    </td>
                    <td className="py-2 text-right" style={{ color: row.freq_b > 0 ? "#4a9eed" : "var(--muted)" }}>
                      {row.freq_b}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
