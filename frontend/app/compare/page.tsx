import { api } from "@/lib/api";
import ComparePageClient from "@/components/ComparePageClient";

export default async function ComparePage() {
  const terms = await api.terms();

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold mb-1">Compare Terms</h1>
        <p style={{ color: "var(--muted)" }} className="text-sm">
          Overlay up to 6 terms on the same chart to compare prominence over time. Select from the dropdown or type any Chinese term to search documents directly.
        </p>
      </div>
      <ComparePageClient terms={terms} />
    </div>
  );
}
