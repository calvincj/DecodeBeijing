"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Term } from "@/lib/api";

interface Props {
  terms: Term[];
  defaultA?: number;
  defaultB?: number;
}

export default function CompareSelector({ terms, defaultA, defaultB }: Props) {
  const router = useRouter();
  const [a, setA] = useState(defaultA ?? terms[0]?.id ?? 0);
  const [b, setB] = useState(defaultB ?? terms[1]?.id ?? 0);

  const selectStyle = {
    background: "var(--bg)",
    border: "1px solid var(--border)",
    color: "var(--text)",
    borderRadius: 6,
    padding: "6px 10px",
    fontSize: 14,
    width: "100%",
  };

  return (
    <div className="flex gap-3 items-end flex-wrap mb-6">
      <div className="flex-1 min-w-40">
        <label className="text-xs mb-1 block" style={{ color: "var(--muted)" }}>Term A</label>
        <select style={selectStyle} value={a} onChange={(e) => setA(Number(e.target.value))}>
          {terms.map((t) => (
            <option key={t.id} value={t.id}>{t.term_zh} — {t.term_en}</option>
          ))}
        </select>
      </div>
      <div className="flex-1 min-w-40">
        <label className="text-xs mb-1 block" style={{ color: "var(--muted)" }}>Term B</label>
        <select style={selectStyle} value={b} onChange={(e) => setB(Number(e.target.value))}>
          {terms.map((t) => (
            <option key={t.id} value={t.id}>{t.term_zh} — {t.term_en}</option>
          ))}
        </select>
      </div>
      <button
        onClick={() => router.push(`/compare?a=${a}&b=${b}`)}
        className="px-4 py-2 rounded-lg text-sm font-medium transition-opacity hover:opacity-80"
        style={{ background: "var(--accent)", color: "#fff" }}
      >
        Compare
      </button>
    </div>
  );
}
