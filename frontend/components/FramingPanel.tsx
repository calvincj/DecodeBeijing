"use client";

import { FrequencyPoint, FramingPoint } from "@/lib/api";

// ── Tone word lists ───────────────────────────────────────────────────────────
// Ordered longest-first so compound phrases beat their components at same position.

const PRE_TONE: { word: string; tone: "promote" | "caution" | "stable" }[] = [
  // Promoting
  { word: "坚决推进", tone: "promote" }, { word: "大力推进", tone: "promote" },
  { word: "加快推进", tone: "promote" }, { word: "积极推进", tone: "promote" },
  { word: "着力推进", tone: "promote" }, { word: "全面推进", tone: "promote" },
  { word: "大力发展", tone: "promote" }, { word: "加快发展", tone: "promote" },
  { word: "积极发展", tone: "promote" }, { word: "因地制宜发展", tone: "promote" },
  { word: "加大力度", tone: "promote" }, { word: "大力支持", tone: "promote" },
  { word: "积极培育", tone: "promote" }, { word: "加快培育", tone: "promote" },
  { word: "强化", tone: "promote" },
  { word: "大力", tone: "promote" }, { word: "深化", tone: "promote" },
  { word: "加快", tone: "promote" }, { word: "加大", tone: "promote" },
  { word: "扩大", tone: "promote" }, { word: "积极", tone: "promote" },
  { word: "着力", tone: "promote" }, { word: "全力", tone: "promote" },
  { word: "促进", tone: "promote" }, { word: "推动", tone: "promote" },
  { word: "壮大", tone: "promote" }, { word: "培育", tone: "promote" },
  { word: "鼓励", tone: "promote" }, { word: "激发", tone: "promote" },
  { word: "释放", tone: "promote" }, { word: "提升", tone: "promote" },
  { word: "发展", tone: "promote" }, { word: "推进", tone: "promote" },
  // Cautioning
  { word: "坚决打击", tone: "caution" }, { word: "坚决遏制", tone: "caution" },
  { word: "坚决防止", tone: "caution" }, { word: "严厉打击", tone: "caution" },
  { word: "严格管控", tone: "caution" },
  { word: "防止", tone: "caution" }, { word: "防范", tone: "caution" },
  { word: "遏制", tone: "caution" }, { word: "打击", tone: "caution" },
  { word: "管控", tone: "caution" }, { word: "严控", tone: "caution" },
  { word: "防控", tone: "caution" }, { word: "严禁", tone: "caution" },
  { word: "禁止", tone: "caution" }, { word: "杜绝", tone: "caution" },
  { word: "整治", tone: "caution" }, { word: "惩处", tone: "caution" },
  { word: "取缔", tone: "caution" }, { word: "纠正", tone: "caution" },
  { word: "抵制", tone: "caution" }, { word: "抑制", tone: "caution" },
  { word: "化解", tone: "caution" }, { word: "防御", tone: "caution" },
  // Stabilizing
  { word: "毫不动摇", tone: "stable" }, { word: "长期坚持", tone: "stable" },
  { word: "始终坚持", tone: "stable" },
  { word: "坚持", tone: "stable" }, { word: "维护", tone: "stable" },
  { word: "确保", tone: "stable" }, { word: "保持", tone: "stable" },
  { word: "巩固", tone: "stable" }, { word: "守住", tone: "stable" },
  { word: "坚守", tone: "stable" }, { word: "落实", tone: "stable" },
  { word: "贯彻", tone: "stable" }, { word: "不动摇", tone: "stable" },
  { word: "延续", tone: "stable" }, { word: "稳住", tone: "stable" },
];

// Words that appear AFTER the term and describe it
const POST_TONE: { word: string; tone: "promote" | "caution" | "stable" }[] = [
  { word: "贯穿始终", tone: "stable" }, { word: "始终如一", tone: "stable" },
  { word: "长期坚持", tone: "stable" }, { word: "持续推进", tone: "stable" },
  { word: "不断深化", tone: "promote" }, { word: "不断完善", tone: "promote" },
  { word: "取得突破", tone: "promote" }, { word: "取得重大成果", tone: "promote" },
  { word: "面临风险", tone: "caution" }, { word: "存在隐患", tone: "caution" },
  { word: "仍需警惕", tone: "caution" }, { word: "不可忽视", tone: "caution" },
];

const META = {
  promote:  { label: "Promoting",   bg: "#34d39922", text: "#34d399", icon: "↑" },
  caution:  { label: "Cautioning",  bg: "#e85d4a22", text: "#e85d4a", icon: "⚠" },
  stable:   { label: "Stabilizing", bg: "#4a9eed22", text: "#4a9eed", icon: "→" },
  neutral:  { label: "Neutral",     bg: "var(--border)", text: "#64748b", icon: "·" },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

const CLAUSE_PUNCT = /[，。！？；\n]/;
const TOC_RE = /^\d{1,4}第|^第[一二三四五六七八九十百]+[篇章节].*[^，。！？；]$|\.{3,}/;

// Returns true if the snippet (or the clause containing termZh) looks like a ToC line
function isToC(snippet: string, termZh: string): boolean {
  if (TOC_RE.test(snippet.trim())) return true;
  const idx = snippet.indexOf(termZh);
  if (idx === -1) return false;
  // Check the clause containing the term
  let lo = idx;
  while (lo > 0 && !CLAUSE_PUNCT.test(snippet[lo - 1])) lo--;
  let hi = idx + termZh.length;
  while (hi < snippet.length && !CLAUSE_PUNCT.test(snippet[hi])) hi++;
  const clause = snippet.slice(lo, hi);
  return TOC_RE.test(clause.trim());
}

// Get just the clause containing the term: text between surrounding clause punctuation
function getClause(snippet: string, termZh: string): { pre: string; post: string } {
  const idx = snippet.indexOf(termZh);
  if (idx === -1) return { pre: "", post: "" };
  let lo = idx;
  while (lo > 0 && !CLAUSE_PUNCT.test(snippet[lo - 1])) lo--;
  let hi = idx + termZh.length;
  while (hi < snippet.length && !CLAUSE_PUNCT.test(snippet[hi])) hi++;
  return {
    pre:  snippet.slice(lo, idx),
    post: snippet.slice(idx + termZh.length, hi),
  };
}

// Find rightmost (closest to term) tone word; for ties at same endPos, first match wins (longest).
function rightmostMatch(
  text: string,
  list: typeof PRE_TONE
): { word: string; tone: "promote" | "caution" | "stable" } | null {
  let bestWord: string | null = null;
  let bestEnd = -1;
  let bestTone: "promote" | "caution" | "stable" = "promote";
  for (const { word, tone } of list) {
    const pos = text.lastIndexOf(word);
    if (pos === -1) continue;
    const end = pos + word.length;
    if (end > bestEnd) { bestEnd = end; bestWord = word; bestTone = tone; }
  }
  return bestWord ? { word: bestWord, tone: bestTone } : null;
}

// Strip PDF-artifact spaces/newlines between Chinese characters
function cleanZh(s: string): string {
  let r = s.replace(/\n/g, "");
  r = r.replace(/([一-鿿＀-￯，。！？；、：「」【】《》""''])\s+([一-鿿＀-￯，。！？；、：「」【】《》""''])/g, "$1$2");
  r = r.replace(/([一-鿿＀-￯，。！？；、：「」【】《》""''])\s+([一-鿿＀-￯，。！？；、：「」【】《》""''])/g, "$1$2");
  return r.trim();
}

// Build excerpt spanning from toneWord position through end of term's clause
function buildExcerpt(snippet: string, termZh: string, toneWord?: string | null): string {
  const idx = snippet.indexOf(termZh);
  if (idx === -1) return "";
  let leftAnchor = idx;
  if (toneWord) {
    const wp = snippet.lastIndexOf(toneWord, idx);
    if (wp !== -1) leftAnchor = wp;
  }
  let lo = leftAnchor;
  while (lo > 0 && !CLAUSE_PUNCT.test(snippet[lo - 1])) lo--;
  let hi = idx + termZh.length;
  while (hi < snippet.length && !/[，。！？；\n]/.test(snippet[hi])) hi++;
  if (hi < snippet.length) hi++;
  return cleanZh(snippet.slice(lo, hi).trim());
}

interface DetectResult {
  tone: keyof typeof META;
  word: string | null;
  excerpt: string;
}

function detectHardcoded(snippets: string[], termZh: string): DetectResult {
  const candidates: Array<{ word: string; tone: keyof typeof META; snippet: string; isPost: boolean }> = [];

  for (const snippet of snippets) {
    if (isToC(snippet, termZh)) continue; // skip ToC lines

    const idx = snippet.indexOf(termZh);
    if (idx === -1) continue;

    const { pre, post } = getClause(snippet, termZh);

    const preMatch  = rightmostMatch(pre, PRE_TONE);
    const postMatch = rightmostMatch(post, POST_TONE);

    if (preMatch)  candidates.push({ ...preMatch,  snippet, isPost: false });
    if (postMatch) candidates.push({ ...postMatch, snippet, isPost: true  });
  }

  if (!candidates.length) {
    const src = snippets.find((s) => s.includes(termZh) && !isToC(s, termZh)) ?? "";
    return { tone: "neutral", word: null, excerpt: cleanZh(buildExcerpt(src, termZh)) };
  }

  // Count by word, prefer pre-term matches in ties
  const counts: Record<string, { tone: keyof typeof META; n: number; snippet: string; isPost: boolean }> = {};
  for (const c of candidates) {
    if (!counts[c.word]) counts[c.word] = { tone: c.tone, n: 0, snippet: c.snippet, isPost: c.isPost };
    counts[c.word].n++;
  }
  const [word, { tone, snippet }] = Object.entries(counts)
    .sort((a, b) => b[1].n - a[1].n || (a[1].isPost ? 1 : -1))[0];

  return { tone, word, excerpt: buildExcerpt(snippet, termZh, word) };
}

// ── Component ─────────────────────────────────────────────────────────────────

const ATTITUDE_TONE: Record<string, keyof typeof META> = {
  promoting:   "promote",
  cautioning:  "caution",
  stabilizing: "stable",
  neutral:     "neutral",
};

interface Props {
  freq: FrequencyPoint[];
  termZh: string;
  cachedFraming?: FramingPoint[];
}

export default function FramingPanel({ freq, termZh, cachedFraming = [] }: Props) {
  const framingByDoc = Object.fromEntries(cachedFraming.map((f) => [f.document_id, f]));

  const rows = freq
    .filter((p) => p.frequency > 0 && p.context_snippets?.length)
    .map((p) => {
      const cached = framingByDoc[p.document_id];
      let tone: keyof typeof META, word: string | null, excerpt: string;

      if (cached) {
        tone    = ATTITUDE_TONE[cached.attitude] ?? "neutral";
        word    = cached.key_phrase ?? null;
        // Build excerpt from stored snippets using the API's key_phrase as anchor
        const src = p.context_snippets!.find((s) => s.includes(termZh) && !isToC(s, termZh)) ?? "";
        excerpt = buildExcerpt(src, termZh, word);
      } else {
        ({ tone, word, excerpt } = detectHardcoded(p.context_snippets!, termZh));
      }

      const meta = META[tone];
      return {
        key: p.document_id,
        year: new Date(p.meeting_date).getFullYear(),
        tone, word, meta, freq: p.frequency, excerpt,
        fromAPI: !!cached,
      };
    });

  if (!rows.length) {
    return <p className="text-xs py-4" style={{ color: "var(--muted)" }}>No context data yet.</p>;
  }

  const apiCount = rows.filter((r) => r.fromAPI).length;

  return (
    <div className="space-y-0">
      <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
        {apiCount > 0
          ? `${apiCount}/${rows.length} from AI analysis · rest from keyword detection`
          : "Keyword detection · run scripts/analyze_framing.py for AI analysis"}
      </p>
      {rows.map((row) => (
        <div key={row.key} className="flex items-center gap-3 py-2"
             style={{ borderBottom: "1px solid var(--border)" }}>
          <span className="w-10 shrink-0 font-mono text-xs" style={{ color: "var(--muted)" }}>
            {row.year}
          </span>
          <span className="text-xs font-medium px-2 py-0.5 rounded-full shrink-0 text-center"
                style={{ background: row.meta.bg, color: row.meta.text, minWidth: "6.5rem" }}>
            {row.meta.icon} {row.meta.label}
          </span>
          <span className="font-medium text-sm shrink-0" style={{ color: row.meta.text, minWidth: "4rem" }}>
            {row.word ?? "—"}
          </span>
          {row.excerpt && (
            <span className="text-xs font-mono" style={{ color: "var(--muted)" }}>
              {row.word && row.excerpt.includes(row.word)
                ? row.excerpt.split(row.word).map((part: string, j: number, arr: string[]) => (
                    <span key={j}>
                      {part}
                      {j < arr.length - 1 && (
                        <mark style={{ background: row.meta.text + "44", color: row.meta.text, borderRadius: 2, padding: "0 2px" }}>
                          {row.word}
                        </mark>
                      )}
                    </span>
                  ))
                : row.excerpt}
            </span>
          )}
          <span className="ml-auto text-xs shrink-0" style={{ color: "var(--muted)" }}>
            ×{row.freq}{row.fromAPI && <span title="AI analysed"> ✦</span>}
          </span>
        </div>
      ))}
    </div>
  );
}
