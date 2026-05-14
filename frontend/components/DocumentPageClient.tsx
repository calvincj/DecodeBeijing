"use client";

import { useState, useMemo } from "react";
import DocumentViewer from "@/components/DocumentViewer";

const SEARCH_COLOR = "#fbbf24";

interface Term {
  term_zh: string;
  category: string;
  frequency: number;
}

interface Props {
  text: string;
  terms: Term[];
  allTermColors: Record<string, string>;
}

export default function DocumentPageClient({ text, terms, allTermColors }: Props) {
  // null = show all; any string = highlight only that string
  const [focus, setFocus] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const top5 = terms.filter((t) => t.frequency >= 2).slice(0, 5);

  // What gets highlighted in the document
  const activeColors: Record<string, string> = useMemo(() => {
    if (focus === null) return allTermColors;
    const color = allTermColors[focus] ?? SEARCH_COLOR;
    return { [focus]: color };
  }, [focus, allTermColors]);

  const focusColor = focus ? (allTermColors[focus] ?? SEARCH_COLOR) : null;

  const hitCount = useMemo(() => {
    if (!focus) return 0;
    let n = 0, i = 0;
    while ((i = text.indexOf(focus, i)) !== -1) { n++; i += focus.length; }
    return n;
  }, [focus, text]);

  function handleSearch(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value;
    setQuery(val);
    setFocus(val || null);
  }

  function handleChip(term: string) {
    setQuery("");
    setFocus((prev) => (prev === term ? null : term));
  }

  function showAll() {
    setFocus(null);
    setQuery("");
  }

  return (
    <>
      <div className="mt-4 space-y-2">
        {/* Chips + show all */}
        <div className="flex flex-wrap gap-2 items-center">
          {top5.map((t) => {
            const color  = allTermColors[t.term_zh] ?? "#64748b";
            const active = focus === t.term_zh;
            const dimmed = focus !== null && !active;
            return (
              <button
                key={t.term_zh}
                onClick={() => handleChip(t.term_zh)}
                style={{
                  background: color + (active ? "44" : "22"),
                  color,
                  outline: active ? `1px solid ${color}` : "none",
                  opacity: dimmed ? 0.35 : 1,
                  cursor: "pointer",
                  fontSize: "0.75rem",
                  padding: "2px 8px",
                  borderRadius: 9999,
                  fontWeight: 500,
                  border: "none",
                }}
              >
                {t.term_zh}
                <span style={{ marginLeft: 4, opacity: 0.6 }}>×{t.frequency}</span>
              </button>
            );
          })}
          <button
            onClick={showAll}
            style={{
              cursor: "pointer",
              fontSize: "0.75rem",
              padding: "2px 8px",
              borderRadius: 9999,
              background: "var(--surface)",
              border: "1px solid var(--border)",
              color: focus !== null ? "var(--fg)" : "var(--muted)",
            }}
          >
            show all
          </button>
        </div>

        {/* Search */}
        <div style={{ position: "relative" }}>
          <input
            type="text"
            value={query}
            onChange={handleSearch}
            placeholder="Search anything in document…"
            style={{
              width: "100%",
              fontSize: "0.75rem",
              padding: "6px 12px",
              paddingRight: focus ? "5rem" : "12px",
              borderRadius: 6,
              outline: "none",
              background: "var(--surface)",
              border: `1px solid ${focus && query ? (focusColor ?? SEARCH_COLOR) : "var(--border)"}`,
              color: "var(--fg)",
              boxSizing: "border-box",
            }}
          />
          {focus && query && (
            <div style={{ position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)", display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: "0.75rem", fontFamily: "monospace", color: focusColor ?? SEARCH_COLOR }}>
                ×{hitCount}
              </span>
              <button onClick={showAll} style={{ fontSize: "0.75rem", color: "var(--muted)", cursor: "pointer", background: "none", border: "none" }}>
                ✕
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="rounded-lg p-6 mt-4"
           style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        <DocumentViewer text={text} termColors={activeColors} />
      </div>
    </>
  );
}
