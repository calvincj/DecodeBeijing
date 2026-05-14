"use client";

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import { RankingPoint } from "@/lib/api";
import { shortTitle } from "@/components/FrequencyChart";

interface Props {
  data: RankingPoint[];
  color?: string;
}

function RankTooltip({
  active, payload, color,
}: {
  active?: boolean;
  payload?: { payload: { position: number; docTitle: string } }[];
  color: string;
}) {
  if (!active || !payload?.length) return null;
  const { position, docTitle } = payload[0].payload;
  return (
    <div style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: 8,
      padding: "8px 12px",
      minWidth: 130,
    }}>
      <span style={{ fontSize: 20, fontWeight: 700, color }}>Task #{position}</span>
      <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 4 }}>
        {shortTitle(docTitle)}
      </div>
    </div>
  );
}

export default function RankingChart({ data, color = "#e85d4a" }: Props) {
  if (!data.length) {
    return (
      <p className="text-sm py-6 text-center" style={{ color: "var(--muted)" }}>
        No policy task list data yet.{" "}
        <span className="font-mono text-xs">
          Run ingest_econconf.py then analyze_document.py to populate.
        </span>
      </p>
    );
  }

  const byYear: Record<string, { year: string; position: number; docTitle: string }> = {};
  for (const r of data) {
    const year = new Date(r.meeting_date).getFullYear().toString();
    if (!byYear[year] || r.position < byYear[year].position) {
      byYear[year] = { year, position: r.position, docTitle: r.title_zh };
    }
  }
  const chartData = Object.values(byYear).sort((a, b) => a.year.localeCompare(b.year));
  const maxPos = Math.max(...chartData.map((d) => d.position), 5);

  return (
    <div>
      <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
        Position in the government's numbered policy task list (Task 1 = top priority).
        A downward trend means the term is being pushed lower down the agenda.
      </p>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="year" tick={{ fill: "var(--muted)", fontSize: 11 }} tickLine={false} />
          <YAxis
            reversed
            domain={[1, maxPos]}
            allowDecimals={false}
            tick={{ fill: "var(--muted)", fontSize: 11 }}
            tickLine={false}
            tickFormatter={(v) => `Task ${v}`}
          />
          <Tooltip content={(props) => <RankTooltip {...(props as any)} color={color} />} />
          <ReferenceLine y={1} stroke={color} strokeDasharray="4 2" strokeOpacity={0.3} />
          <Line
            type="monotone"
            dataKey="position"
            stroke={color}
            strokeWidth={2}
            dot={{ r: 5, fill: color, strokeWidth: 0 }}
            activeDot={{ r: 7 }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
