"use client";

import { useState, useEffect, useRef } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Brush,
} from "recharts";
import { Term, FrequencyPoint, api } from "@/lib/api";

const SLOT_COLORS  = ["#e85d4a", "#4a9eed", "#22c55e", "#fbbf24", "#a78bfa", "#ec4899"];

const CATEGORY_ORDER = [
  "ideological", "macroeconomic", "industrial", "environmental",
  "technology", "livelihood", "diplomatic", "other",
];
const CATEGORY_LABELS: Record<string, string> = {
  ideological:   "Ideological",
  macroeconomic: "Macroeconomic",
  industrial:    "Industrial",
  environmental: "Environmental",
  technology:    "Technology",
  livelihood:    "Livelihood",
  diplomatic:    "Diplomatic",
  other:         "Other",
};
const FILL_TYPES   = new Set(["five_year_plan", "plenum"]);
const FILL_DURATION = 5;

// ─── Smoothing (same logic as FrequencyChart) ─────────────────────────────────

function buildYearFreqs(data: FrequencyPoint[], smooth: boolean): Map<string, number> {
  const sorted = [...data].sort((a, b) => a.meeting_date.localeCompare(b.meeting_date));

  const fillMap    = new Map<string, number>();
  const regularMap = new Map<string, number>();
  const actualYears = new Set<string>();

  for (const p of sorted) {
    const year = p.meeting_date.slice(0, 4);
    actualYears.add(year);
    if (smooth && FILL_TYPES.has(p.meeting_category ?? "") && p.frequency > 0) {
      fillMap.set(year, (fillMap.get(year) ?? 0) + p.frequency);
    } else {
      regularMap.set(year, (regularMap.get(year) ?? 0) + p.frequency);
    }
  }

  if (actualYears.size === 0) return new Map();

  const nums = Array.from(actualYears).sort();
  let minYear = parseInt(nums[0]);
  let maxYear = parseInt(nums[nums.length - 1]);

  if (smooth) {
    for (const year of fillMap.keys()) {
      maxYear = Math.max(maxYear, parseInt(year) + FILL_DURATION - 1);
    }
  }
  maxYear = Math.min(maxYear, new Date().getFullYear());

  const fillYears = Array.from(fillMap.keys()).sort();
  const result = new Map<string, number>();

  for (let y = minYear; y <= maxYear; y++) {
    const year = y.toString();
    let freq = regularMap.get(year) ?? 0;
    if (smooth) {
      for (const pub of fillYears) {
        const p = parseInt(pub);
        if (p <= y && y < p + FILL_DURATION) freq += fillMap.get(pub)!;
      }
    }
    result.set(year, freq);
  }
  return result;
}

// ─── Types ────────────────────────────────────────────────────────────────────

type Slot = {
  id: string;
  color: string;
  termId: number | null;
  label: string;
  data: FrequencyPoint[];
  loading: boolean;
};

let _nextId = 0;
function makeSlot(color: string, term?: Term): Slot {
  return {
    id: `slot-${++_nextId}`,
    color,
    termId: term?.id ?? null,
    label: term?.term_zh ?? "",
    data: [],
    loading: false,
  };
}

// ─── TermPicker ───────────────────────────────────────────────────────────────

function TermPicker({
  terms, slot, onChange, onRemove, canRemove,
}: {
  terms: Term[];
  slot: Slot;
  onChange: (patch: Partial<Slot>) => void;
  onRemove: () => void;
  canRemove: boolean;
}) {
  const [inputValue, setInputValue] = useState(slot.label);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const prevLabel = useRef(slot.label);

  useEffect(() => {
    if (slot.label !== prevLabel.current) {
      setInputValue(slot.label);
      prevLabel.current = slot.label;
    }
  }, [slot.label]);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        setInputValue(slot.label);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [slot.label]);

  const q = inputValue.trim();
  const filtered = q
    ? terms.filter(t =>
        t.term_zh.includes(q) ||
        (t.term_en ?? "").toLowerCase().includes(q.toLowerCase())
      )
    : terms;
  const showCustomOption = q.length > 0 && !terms.some(t => t.term_zh === q);

  async function selectTerm(t: Term) {
    setOpen(false);
    setInputValue(t.term_zh);
    onChange({ termId: t.id, label: t.term_zh, data: [], loading: true });
    const data = await api.frequency(t.id);
    onChange({ data, loading: false });
  }

  async function searchCustom() {
    if (!q) return;
    setOpen(false);
    onChange({ termId: null, label: q, data: [], loading: true });
    const data = await api.searchFrequency(q);
    onChange({ data, loading: false });
  }

  return (
    <div ref={containerRef} style={{ position: "relative" }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 6,
        border: "1px solid var(--border)", borderRadius: 6,
        padding: "5px 8px", background: "var(--bg)",
      }}>
        <span style={{
          width: 10, height: 10, borderRadius: "50%",
          background: slot.color, flexShrink: 0,
        }} />
        <input
          value={inputValue}
          onChange={e => { setInputValue(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          placeholder="Search terms…"
          style={{
            flex: 1, background: "transparent", border: "none",
            outline: "none", fontSize: 13, color: "var(--fg)",
          }}
        />
        {slot.loading && (
          <span style={{ fontSize: 10, color: "var(--muted)" }}>…</span>
        )}
        {canRemove && (
          <button onClick={onRemove} style={{
            background: "none", border: "none", cursor: "pointer",
            color: "var(--muted)", fontSize: 16, padding: 0, lineHeight: 1,
          }}>×</button>
        )}
      </div>

      {open && (
        <div style={{
          position: "absolute", top: "calc(100% + 4px)", left: 0, right: 0,
          background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: 6, zIndex: 50, maxHeight: 260, overflowY: "auto",
        }}>
          {q ? (
            // Flat filtered list when searching
            filtered.length > 0 ? filtered.map(t => (
              <button key={t.id} onMouseDown={() => selectTerm(t)} style={{
                width: "100%", textAlign: "left", padding: "6px 10px",
                fontSize: 12, background: "transparent", border: "none",
                borderBottom: "1px solid var(--border)", cursor: "pointer", color: "var(--fg)",
              }}>
                <span style={{ fontWeight: 500 }}>{t.term_zh}</span>
                {t.term_en && <span style={{ color: "var(--muted)", marginLeft: 8 }}>{t.term_en}</span>}
              </button>
            )) : !showCustomOption && (
              <div style={{ padding: "8px 10px", fontSize: 12, color: "var(--muted)" }}>No matches</div>
            )
          ) : (
            // Grouped by category when browsing
            CATEGORY_ORDER.map(cat => {
              const catTerms = terms.filter(t => t.category === cat);
              if (!catTerms.length) return null;
              return (
                <div key={cat}>
                  <div style={{
                    padding: "6px 10px 3px", fontSize: 10, color: "var(--muted)",
                    textTransform: "uppercase", letterSpacing: "0.06em",
                    borderBottom: "1px solid var(--border)",
                  }}>
                    {CATEGORY_LABELS[cat]}
                  </div>
                  {catTerms.map(t => (
                    <button key={t.id} onMouseDown={() => selectTerm(t)} style={{
                      width: "100%", textAlign: "left", padding: "5px 10px 5px 14px",
                      fontSize: 12, background: "transparent", border: "none",
                      borderBottom: "1px solid var(--border)", cursor: "pointer", color: "var(--fg)",
                    }}>
                      <span style={{ fontWeight: 500 }}>{t.term_zh}</span>
                      {t.term_en && <span style={{ color: "var(--muted)", marginLeft: 8 }}>{t.term_en}</span>}
                    </button>
                  ))}
                </div>
              );
            })
          )}
          {showCustomOption && (
            <button onMouseDown={searchCustom} style={{
              width: "100%", textAlign: "left", padding: "6px 10px",
              fontSize: 12, background: "transparent", border: "none",
              cursor: "pointer", color: "var(--muted)", fontStyle: "italic",
            }}>
              Search "{q}" in documents
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Tooltip ──────────────────────────────────────────────────────────────────

function CompareTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const visible = (payload as any[]).filter(p => p.value > 0);
  return (
    <div style={{
      background: "var(--surface)", border: "1px solid var(--border)",
      borderRadius: 8, padding: "8px 12px", minWidth: 130,
    }}>
      <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>{label}</div>
      {(visible.length ? visible : payload).map((p: any) => (
        <div key={p.dataKey} style={{
          fontSize: 13, display: "flex", justifyContent: "space-between",
          gap: 16, color: p.color,
        }}>
          <span>{p.name}</span>
          <span style={{ fontWeight: 600 }}>{p.value}</span>
        </div>
      ))}
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function ComparePageClient({ terms }: { terms: Term[] }) {
  const [smooth, setSmooth] = useState(true);
  const [tipOpen, setTipOpen] = useState(false);
  const [slots, setSlots] = useState<Slot[]>(() => [
    makeSlot(SLOT_COLORS[0], terms[0]),
    makeSlot(SLOT_COLORS[1], terms[1]),
  ]);

  // Fetch data for the two default terms on mount
  useEffect(() => {
    const initial = slots.slice();
    initial.forEach(s => {
      if (s.termId !== null) {
        setSlots(prev => prev.map(x => x.id === s.id ? { ...x, loading: true } : x));
        api.frequency(s.termId).then(data => {
          setSlots(prev => prev.map(x => x.id === s.id ? { ...x, data, loading: false } : x));
        });
      }
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function updateSlot(id: string, patch: Partial<Slot>) {
    setSlots(prev => prev.map(s => s.id === id ? { ...s, ...patch } : s));
  }

  function addSlot() {
    if (slots.length >= SLOT_COLORS.length) return;
    setSlots(prev => [...prev, makeSlot(SLOT_COLORS[prev.length])]);
  }

  function removeSlot(id: string) {
    setSlots(prev => prev.filter(s => s.id !== id));
  }

  // ── Build chart data ──────────────────────────────────────────────────────

  const activeSlots = slots.filter(s => !s.loading && s.label.length > 0);

  const allYears = new Set<string>();
  const slotMaps = activeSlots.map(s => {
    const m = buildYearFreqs(s.data, smooth);
    for (const y of m.keys()) allYears.add(y);
    return { slot: s, map: m };
  });

  let chartData: Record<string, string | number>[] = [];
  if (allYears.size > 0) {
    const sorted = Array.from(allYears).sort();
    const minY = parseInt(sorted[0]);
    const maxY = parseInt(sorted[sorted.length - 1]);
    for (let y = minY; y <= maxY; y++) {
      const point: Record<string, string | number> = { year: y.toString() };
      for (const { slot, map } of slotMaps) {
        point[slot.id] = map.get(y.toString()) ?? 0;
      }
      chartData.push(point);
    }
  }

  const firstActive = chartData.findIndex(p =>
    activeSlots.some(s => (p[s.id] as number) > 0)
  );
  const lastActive  = chartData.reduce((last, p, i) =>
    activeSlots.some(s => (p[s.id] as number) > 0) ? i : last, -1);
  const brushEnd    = lastActive >= 0 ? Math.min(chartData.length - 1, lastActive + 1) : chartData.length - 1;
  const activeSpan  = Math.max(1, lastActive - firstActive);
  const brushStart  = Math.max(0, firstActive - Math.round(activeSpan / 2));
  const labelStep   = chartData.length > 30 ? 5 : chartData.length > 15 ? 2 : 1;

  return (
    <div className="rounded-lg p-4 mb-6"
         style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>

      {/* Term selectors — 2 per row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginBottom: 8 }}>
        {slots.map(slot => (
          <TermPicker
            key={slot.id}
            terms={terms}
            slot={slot}
            onChange={patch => updateSlot(slot.id, patch)}
            onRemove={() => removeSlot(slot.id)}
            canRemove={slots.length > 2}
          />
        ))}
      </div>
      {slots.length < SLOT_COLORS.length && (
        <div style={{ marginBottom: 12 }}>
          <button onClick={addSlot} style={{
            padding: "4px 10px", borderRadius: 6,
            border: "1px dashed var(--border)", background: "transparent",
            color: "var(--muted)", fontSize: 12, cursor: "pointer",
          }}>
            + Add term
          </button>
        </div>
      )}

      {/* Smooth toggle */}
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
        <div style={{ position: "relative", display: "inline-block" }}
             onMouseEnter={() => setTipOpen(true)}
             onMouseLeave={() => setTipOpen(false)}>
          <button
            onClick={() => setSmooth(s => !s)}
            style={{
              fontSize: 11, padding: "2px 8px", borderRadius: 9999,
              border: `1px solid ${smooth ? "var(--fg)" : "var(--border)"}`,
              background: smooth ? "var(--bg)" : "transparent",
              color: smooth ? "var(--fg)" : "var(--muted)", cursor: "pointer",
            }}
          >
            {smooth ? "smoothed" : "raw"}
          </button>
          {tipOpen && (
            <div style={{
              position: "absolute", right: 0, top: "calc(100% + 6px)", width: 240,
              background: "var(--surface)", border: "1px solid var(--border)",
              borderRadius: 8, padding: "8px 10px", fontSize: 11,
              color: "var(--muted)", lineHeight: 1.5, zIndex: 50, pointerEvents: "none",
            }}>
              {smooth
                ? "Plans and plenums are spread across their full term instead of a one-year spike."
                : "Showing exact counts per publication year."}
            </div>
          )}
        </div>
      </div>

      {/* Chart */}
      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="year" tick={{ fill: "var(--muted)", fontSize: 11 }} tickLine={false}
                   interval={0} tickFormatter={(v: string) => parseInt(v) % labelStep === 0 ? v : ""} />
            <YAxis tick={{ fill: "var(--muted)", fontSize: 11 }} tickLine={false} allowDecimals={false} />
            <Tooltip content={(props) => <CompareTooltip {...props} />} />
            {activeSlots.map(s => (
              <Line key={s.id} type="monotone" dataKey={s.id} name={s.label}
                    stroke={s.color} strokeWidth={2}
                    dot={{ r: 3, fill: s.color, strokeWidth: 0 }}
                    activeDot={{ r: 5 }} />
            ))}
            {chartData.length > 6 && (
              <Brush dataKey="year" height={24} stroke="var(--border)"
                     fill="var(--surface)" travellerWidth={6}
                     startIndex={brushStart} endIndex={brushEnd}
                     tickFormatter={() => ""} />
            )}
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <p style={{ color: "var(--muted)" }} className="text-sm py-8 text-center">
          Select terms above to compare.
        </p>
      )}
    </div>
  );
}
