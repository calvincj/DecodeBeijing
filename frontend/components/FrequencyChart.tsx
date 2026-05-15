"use client";

import { useState } from "react";
import {
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Area, AreaChart, Brush,
} from "recharts";
import { FrequencyPoint } from "@/lib/api";

interface Props {
  data: FrequencyPoint[];
  color?: string;
}

function cnOrdToNum(cn: string): number {
  const d: Record<string, number> = { 一:1,二:2,三:3,四:4,五:5,六:6,七:7,八:8,九:9 };
  if (cn === "十") return 10;
  if (cn.startsWith("二十")) return 20 + (d[cn[2]] ?? 0);
  if (cn.startsWith("十"))   return 10 + (d[cn[1]] ?? 0);
  return d[cn] ?? 0;
}

export function shortTitle(title: string): string {
  if (/政府工作报告/.test(title)) return "政府工作报告";
  if (/经济工作会议/.test(title)) return "经济工作会议";
  const fyp = title.match(/第([一二三四五六七八九十]+)个五年/);
  if (fyp) return fyp[1] + "五";
  const plenum = title.match(/第([一二三四五六七八九十]+)届中央委员会第三次/);
  if (plenum) return cnOrdToNum(plenum[1]) + "届三全会";
  return title.slice(0, 12);
}

interface DocEntry { title: string; freq: number; spread: boolean; }
interface YearPoint { date: string; freq: number; docs: DocEntry[]; }

const FILL_TYPES = new Set(["five_year_plan", "plenum"]);
const FILL_DURATION = 5;

function buildChartData(data: FrequencyPoint[], smooth: boolean): YearPoint[] {
  const sorted = [...data].sort((a, b) => a.meeting_date.localeCompare(b.meeting_date));

  const fillMap    = new Map<string, DocEntry[]>(); // fill-type docs keyed by publication year
  const regularMap = new Map<string, DocEntry[]>(); // all other docs keyed by year
  const actualYears = new Set<string>();

  for (const p of sorted) {
    const year = p.meeting_date.slice(0, 4);
    actualYears.add(year);

    if (smooth && FILL_TYPES.has(p.meeting_category ?? "")) {
      if (!fillMap.has(year)) fillMap.set(year, []);
      fillMap.get(year)!.push({ title: p.title_zh, freq: p.frequency, spread: false });
    } else {
      if (!regularMap.has(year)) regularMap.set(year, []);
      regularMap.get(year)!.push({ title: p.title_zh, freq: p.frequency, spread: false });
    }
  }

  if (actualYears.size === 0) return [];

  const nums = Array.from(actualYears).sort();
  let minYear = parseInt(nums[0]);
  let maxYear = parseInt(nums[nums.length - 1]);

  // Extend range to cover each fill-type doc's full duration, capped at current year
  if (smooth) {
    const currentYear = new Date().getFullYear();
    for (const year of fillMap.keys()) {
      maxYear = Math.min(
        Math.max(maxYear, parseInt(year) + FILL_DURATION - 1),
        currentYear,
      );
    }
  }

  const fillYears = Array.from(fillMap.keys()).sort();
  const allYears: string[] = [];
  for (let y = minYear; y <= maxYear; y++) allYears.push(y.toString());

  return allYears.map((year) => {
    const seen = new Set<string>();
    let freq = 0;
    const docs: DocEntry[] = [];

    const addEntry = (e: DocEntry) => {
      if (seen.has(e.title)) return;
      seen.add(e.title);
      freq += e.freq;
      if (e.freq > 0) docs.push(e);
    };

    for (const e of regularMap.get(year) ?? []) addEntry(e);

    // Window-based fill: a fill-type doc covers [pubYear, pubYear + FILL_DURATION).
    // All overlapping windows contribute their freq independently.
    if (smooth && fillYears.length > 0) {
      const yr = parseInt(year);
      for (const pubStr of fillYears) {
        const pub = parseInt(pubStr);
        if (pub <= yr && yr < pub + FILL_DURATION) {
          const isSpread = pub !== yr;
          for (const e of fillMap.get(pubStr)!) addEntry({ ...e, spread: isSpread });
        }
      }
    }

    docs.sort((a, b) => b.freq - a.freq);
    return { date: year, freq, docs };
  });
}

function FreqTooltip({
  active, payload, color,
}: {
  active?: boolean;
  payload?: { payload: YearPoint }[];
  color: string;
}) {
  if (!active || !payload?.length) return null;
  const { freq, docs } = payload[0].payload;
  return (
    <div style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: 8,
      padding: "8px 12px",
      minWidth: 140,
    }}>
      <span style={{ fontSize: 20, fontWeight: 700, color: freq > 0 ? color : "var(--muted)" }}>
        {freq}
      </span>
      <span style={{ fontSize: 12, color: "var(--muted)", marginLeft: 5 }}>
        mention{freq !== 1 ? "s" : ""}
      </span>
      {docs.length > 0 && (
        <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 2 }}>
          {docs.map((d, i) => (
            <div key={i} style={{ fontSize: 11, display: "flex", justifyContent: "space-between", gap: 12 }}>
              <span style={{ color: "var(--muted)" }}>{shortTitle(d.title)}</span>
              <span style={{ color: d.spread ? "var(--muted)" : color }}>
                {d.spread ? "↳ " : ""}{d.freq}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function FrequencyChart({ data, color = "#e85d4a" }: Props) {
  const [smooth, setSmooth]   = useState(true);
  const [tipOpen, setTipOpen] = useState(false);

  const chartData = buildChartData(data, smooth);

  const firstActive = chartData.findIndex((p) => p.freq > 0);
  const lastActive  = chartData.reduce((last, p, i) => (p.freq > 0 ? i : last), -1);
  const brushEnd    = lastActive >= 0 ? Math.min(chartData.length - 1, lastActive + 1) : chartData.length - 1;

  const activeSpan = Math.max(1, lastActive - firstActive);
  const preContext = Math.round(activeSpan / 2);
  const brushStart = Math.max(0, firstActive - preContext);

  const maxFreq = Math.max(...chartData.map((d) => d.freq), 0);
  const yMax    = maxFreq + 2;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
        <div style={{ position: "relative", display: "inline-block" }}
             onMouseEnter={() => setTipOpen(true)}
             onMouseLeave={() => setTipOpen(false)}>
          <button
            onClick={() => setSmooth((s) => !s)}
            style={{
              fontSize: 11,
              padding: "2px 8px",
              borderRadius: 9999,
              border: `1px solid ${smooth ? color : "var(--border)"}`,
              background: smooth ? color + "22" : "transparent",
              color: smooth ? color : "var(--muted)",
              cursor: "pointer",
            }}
          >
            {smooth ? "smoothed" : "raw"}
          </button>
          {tipOpen && (
            <div style={{
              position: "absolute",
              right: 0,
              top: "calc(100% + 6px)",
              width: 240,
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "8px 10px",
              fontSize: 11,
              color: "var(--muted)",
              lineHeight: 1.5,
              zIndex: 50,
              pointerEvents: "none",
            }}>
              {smooth
                ? "Plans and plenums cover several years, so their mentions are shown across that whole period instead of as a one-year spike. Click to see exact yearly counts."
                : "Showing exact counts for the year each document was published. Click to spread plans and plenums across their full term."}
            </div>
          )}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="freqGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="date" tick={{ fill: "var(--muted)", fontSize: 11 }} tickLine={false} interval={0} />
          <YAxis tick={{ fill: "var(--muted)", fontSize: 11 }} tickLine={false} allowDecimals={false} domain={[0, yMax]} />
          <Tooltip content={(props) => <FreqTooltip {...(props as any)} color={color} />} />
          <ReferenceLine y={0} stroke="var(--border)" />
          <Area type="monotone" dataKey="freq" stroke={color} strokeWidth={2}
                fill="url(#freqGrad)" dot={{ r: 4, fill: color, strokeWidth: 0 }}
                activeDot={(props: any) => {
                  const { cx, cy } = props;
                  if (!isFinite(cx) || !isFinite(cy)) return <g />;
                  return <circle cx={cx} cy={cy} r={6} fill={color} />;
                }} />
          {chartData.length > 6 && (
            <Brush dataKey="date" height={24} stroke="var(--border)"
                   fill="var(--surface)" travellerWidth={6}
                   startIndex={brushStart} endIndex={brushEnd}
                   tickFormatter={() => ""}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
