"use client";

import { useMemo } from "react";

interface Props {
  text: string;
  termColors: Record<string, string>;
}

interface Highlight {
  start: number;
  end: number;
  color: string;
}

// Dot-leader ToC line: ends with 4+ dots/ellipsis + page number
const TOC_ENTRY_RE = /^(.+?)[\s.…]{4,}(\d+)\s*$/;
// Chapter/section heading in body text (no trailing dots)
const HEADING_RE = /^第[一二三四五六七八九十百]+[篇章节]/;
// A line ending with these closes a paragraph buffer
const SENTENCE_END = /[。！？」』]$/;

type Segment =
  | { type: "toc-entry"; heading: string; page: string }
  | { type: "heading";   text: string }
  | { type: "para";      text: string };

function processText(raw: string): Segment[] {
  const lines = raw.split("\n").map((l) => l.trim()).filter((l) => l.length > 0);
  const segments: Segment[] = [];
  let buf: string[] = [];

  const flush = () => {
    if (buf.length) {
      segments.push({ type: "para", text: buf.join("") });
      buf = [];
    }
  };

  for (const line of lines) {
    const tocMatch = TOC_ENTRY_RE.exec(line);
    if (tocMatch) {
      // ToC entry with dot leaders — render with heading + page number
      flush();
      segments.push({ type: "toc-entry", heading: tocMatch[1].trim(), page: tocMatch[2] });
    } else if (HEADING_RE.test(line)) {
      // Chapter/section heading in body text
      flush();
      segments.push({ type: "heading", text: line });
    } else {
      // Regular text — accumulate; flush when a sentence ends
      buf.push(line);
      if (SENTENCE_END.test(line)) flush();
    }
  }
  flush();
  return segments;
}

function getHighlights(text: string, termColors: Record<string, string>): Highlight[] {
  const raw: Highlight[] = [];
  for (const [term, color] of Object.entries(termColors)) {
    let idx = 0;
    while (idx < text.length) {
      const pos = text.indexOf(term, idx);
      if (pos === -1) break;
      raw.push({ start: pos, end: pos + term.length, color });
      idx = pos + term.length;
    }
  }
  raw.sort((a, b) => a.start - b.start || b.end - a.end);
  const resolved: Highlight[] = [];
  let cursor = 0;
  for (const h of raw) {
    if (h.start >= cursor) { resolved.push(h); cursor = h.end; }
  }
  return resolved;
}

function HighlightedText({ text, termColors }: { text: string; termColors: Record<string, string> }) {
  const highlights = useMemo(() => getHighlights(text, termColors), [text, termColors]);
  if (!highlights.length) return <>{text}</>;
  const parts: React.ReactNode[] = [];
  let cursor = 0;
  for (const h of highlights) {
    if (h.start > cursor) parts.push(text.slice(cursor, h.start));
    parts.push(
      <mark key={h.start}
            style={{ background: h.color + "44", color: h.color, borderRadius: 2, padding: "0 1px" }}>
        {text.slice(h.start, h.end)}
      </mark>
    );
    cursor = h.end;
  }
  if (cursor < text.length) parts.push(text.slice(cursor));
  return <>{parts}</>;
}

export default function DocumentViewer({ text, termColors }: Props) {
  const segments = useMemo(() => processText(text), [text]);

  return (
    <div style={{ color: "var(--fg)", lineHeight: 2 }}>
      {segments.map((seg, i) => {
        if (seg.type === "toc-entry") {
          return (
            <div key={i} className="flex items-baseline gap-2 py-0.5">
              <span className="text-sm shrink-0">
                <HighlightedText text={seg.heading} termColors={termColors} />
              </span>
              <span className="flex-1 border-b border-dotted mx-1"
                    style={{ borderColor: "var(--border)", minWidth: "1rem" }} />
              <span className="text-xs shrink-0" style={{ color: "var(--muted)" }}>
                {seg.page}
              </span>
            </div>
          );
        }
        if (seg.type === "heading") {
          return (
            <p key={i} className="mt-5 mb-1 font-semibold text-sm">
              <HighlightedText text={seg.text} termColors={termColors} />
            </p>
          );
        }
        return (
          <p key={i} className="text-sm mb-2">
            <HighlightedText text={seg.text} termColors={termColors} />
          </p>
        );
      })}
    </div>
  );
}
