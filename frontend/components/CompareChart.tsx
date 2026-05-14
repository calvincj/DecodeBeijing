"use client";

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, Brush,
} from "recharts";
import { CompareResult } from "@/lib/api";

interface Props {
  data: CompareResult;
}

function fmt(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("en-US", { year: "numeric", month: "short" });
}

export default function CompareChart({ data }: Props) {
  const sorted = [...data.series].sort((a, b) =>
    a.meeting_date.localeCompare(b.meeting_date)
  );

  const termA = data.term_a.term_zh;
  const termB = data.term_b.term_zh;

  const chartData = sorted.map((p) => ({
    date:    fmt(p.meeting_date),
    rawDate: p.meeting_date,
    [termA]: p.freq_a,
    [termB]: p.freq_b,
    title:   p.title_zh,
  }));

  const firstActive = chartData.findIndex((p) => (p[termA] as number) > 0 || (p[termB] as number) > 0);
  const lastActive  = chartData.reduce((last, p, i) =>
    ((p[termA] as number) > 0 || (p[termB] as number) > 0) ? i : last, -1);
  const brushEnd = lastActive >= 0 ? Math.min(chartData.length - 1, lastActive + 1) : chartData.length - 1;

  const activeSpan = Math.max(1, lastActive - firstActive);
  const preContext = Math.round(activeSpan / 2);
  const brushStart = Math.max(0, firstActive - preContext);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey="date" tick={{ fill: "var(--muted)", fontSize: 11 }} tickLine={false} />
        <YAxis tick={{ fill: "var(--muted)", fontSize: 11 }} tickLine={false} allowDecimals={false} />
        <Tooltip
          contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8 }}
          labelStyle={{ color: "var(--fg)", marginBottom: 4 }}
          labelFormatter={(_, payload) => payload?.[0]?.payload?.title ?? ""}
        />
        <Legend wrapperStyle={{ color: "var(--fg)", fontSize: 12, paddingTop: 8 }} />
        <Line type="monotone" dataKey={data.term_a.term_zh}
              stroke="#e85d4a" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
        <Line type="monotone" dataKey={data.term_b.term_zh}
              stroke="#4a9eed" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
        {chartData.length > 6 && (
          <Brush dataKey="date" height={24} stroke="var(--border)"
                 fill="var(--surface)" travellerWidth={6}
                 startIndex={brushStart} endIndex={brushEnd}
                 tickFormatter={() => ""}
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}
