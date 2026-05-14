"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Document } from "@/lib/api";

const CATEGORY_META: Record<string, { label: string; color: string }> = {
  economic_work_conference: { label: "Central Economic Work Conference", color: "#34d399" },
  five_year_plan:           { label: "Five-Year Plans",                  color: "#4a9eed" },
  two_sessions_national:    { label: "Two Sessions (National)",          color: "#fbbf24" },
  party_congress:           { label: "Party Congress",                   color: "#e85d4a" },
  plenum:                   { label: "Third Plenary Session",             color: "#f97316" },
  politburo:                { label: "Politburo Meeting",                color: "#a78bfa" },
  other:                    { label: "Other",                            color: "#64748b" },
};

const ORDER = ["economic_work_conference", "five_year_plan", "two_sessions_national", "party_congress", "plenum", "politburo", "other"];

function DocGroup({
  category, docs, selected, onToggle,
}: {
  category: string;
  docs: Document[];
  selected: Set<number>;
  onToggle: (id: number) => void;
}) {
  const [open, setOpen] = useState(true);
  const meta = CATEGORY_META[category] ?? { label: category, color: "#64748b" };
  const allChecked = docs.every((d) => selected.has(d.id));
  const someChecked = docs.some((d) => selected.has(d.id));

  const toggleAll = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (allChecked) docs.forEach((d) => onToggle(d.id));
    else docs.filter((d) => !selected.has(d.id)).forEach((d) => onToggle(d.id));
  };

  return (
    <div className="mb-4 rounded-lg overflow-hidden"
         style={{ border: "1px solid var(--border)" }}>
      <div className="flex items-center px-4 py-3 gap-3"
           style={{ background: "var(--surface)" }}>
        {/* Group-level checkbox */}
        <input
          type="checkbox"
          checked={allChecked}
          ref={(el) => { if (el) el.indeterminate = someChecked && !allChecked; }}
          onChange={() => {}}
          onClick={toggleAll}
          className="w-4 h-4 shrink-0 cursor-pointer"
        />
        <button onClick={() => setOpen((o) => !o)}
                className="flex items-center gap-3 flex-1 text-left">
          <span className="text-xs font-medium px-2 py-0.5 rounded-full"
                style={{ background: meta.color + "22", color: meta.color }}>
            {meta.label}
          </span>
          <span className="text-sm" style={{ color: "var(--muted)" }}>
            {docs.length} document{docs.length !== 1 ? "s" : ""}
          </span>
          <span className="ml-auto" style={{ color: "var(--muted)" }}>{open ? "▾" : "▸"}</span>
        </button>
      </div>

      {open && (
        <div style={{ borderTop: "1px solid var(--border)" }}>
          {docs.map((doc, i) => (
            <div key={doc.id}
                 className="flex items-center gap-3 px-4 py-2.5"
                 style={{ borderTop: i > 0 ? "1px solid var(--border)" : undefined }}>
              <input
                type="checkbox"
                checked={selected.has(doc.id)}
                onChange={() => onToggle(doc.id)}
                className="w-4 h-4 shrink-0 cursor-pointer"
                onClick={(e) => e.stopPropagation()}
              />
              <Link href={`/documents/${doc.id}`}
                    className="flex items-center justify-between gap-4 flex-1 hover:opacity-80 transition-opacity">
                <span className="text-sm">{doc.title_zh}</span>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-xs" style={{ color: "var(--muted)" }}>{doc.meeting_date}</span>
                  {doc.word_count_zh && (
                    <span className="text-xs" style={{ color: "var(--muted)" }}>
                      {(doc.word_count_zh / 1000).toFixed(0)}k chars
                    </span>
                  )}
                  <span className="text-xs" style={{ color: meta.color }}>→</span>
                </div>
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    api.documents().then((d) => { setDocs(d); setLoading(false); });
  }, []);

  const toggle = (id: number) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const downloadSelected = async () => {
    if (!selected.size || downloading) return;
    setDownloading(true);
    const parts: string[] = [];
    for (const id of Array.from(selected)) {
      const doc = docs.find((d) => d.id === id);
      try {
        const detail = await api.document(id);
        const sep = "=".repeat(60);
        parts.push(`${sep}\n${detail.title_zh}\n${detail.meeting_date}\n${sep}\n\n${detail.raw_text_zh}`);
      } catch {
        parts.push(`// Could not load document ${doc?.title_zh ?? id}`);
      }
    }
    const blob = new Blob([parts.join("\n\n\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = selected.size === 1
      ? `${docs.find((d) => d.id === Array.from(selected)[0])?.title_zh ?? "document"}.txt`
      : `decode-beijing-${selected.size}-docs.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setDownloading(false);
  };

  const grouped: Record<string, Document[]> = {};
  for (const doc of docs) {
    const key = doc.meeting_category ?? "other";
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(doc);
  }
  for (const key of Object.keys(grouped)) {
    grouped[key].sort((a, b) => b.meeting_date.localeCompare(a.meeting_date));
  }
  const categories = ORDER.filter((k) => grouped[k]);

  return (
    <div className="max-w-4xl mx-auto pb-24">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold mb-1">Documents</h1>
        <p style={{ color: "var(--muted)" }} className="text-sm">
          {loading ? "Loading…" : `${docs.length} document${docs.length !== 1 ? "s" : ""} · click to read full text`}
        </p>
      </div>

      {loading ? (
        <p style={{ color: "var(--muted)" }} className="text-sm">Loading…</p>
      ) : (
        categories.map((cat) => (
          <DocGroup key={cat} category={cat} docs={grouped[cat]}
                    selected={selected} onToggle={toggle} />
        ))
      )}

      {/* Floating action bar when docs are selected */}
      {selected.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-4 px-5 py-3 rounded-full shadow-lg z-50"
             style={{ background: "#1e2130", border: "1px solid var(--border)" }}>
          <span className="text-sm" style={{ color: "var(--muted)" }}>
            {selected.size} selected
          </span>
          <button
            onClick={() => setSelected(new Set())}
            className="text-xs px-3 py-1 rounded-full hover:bg-white/10 transition-colors"
            style={{ color: "var(--muted)" }}>
            Clear
          </button>
          <button
            onClick={downloadSelected}
            disabled={downloading}
            className="text-xs font-medium px-4 py-1.5 rounded-full transition-colors"
            style={{ background: "#4a9eed22", color: "#4a9eed", opacity: downloading ? 0.6 : 1 }}>
            {downloading ? "Downloading…" : "↓ Download .txt"}
          </button>
        </div>
      )}
    </div>
  );
}
