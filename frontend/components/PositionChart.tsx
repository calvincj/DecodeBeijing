"use client";

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import { FrequencyPoint } from "@/lib/api";

interface Props {
  data: FrequencyPoint[];
  color?: string;
}

// Priority score: 100 = mentioned in first sentence, 0 = mentioned at the very end.
// A rising line = term is moving earlier in the document = getting more emphasis.
function priorityScore(p: FrequencyPoint): number | null {
  if (p.first_char_position == null || !p.doc_word_count) return null;
  return Math.round((1 - p.first_char_position / p.doc_word_count) * 100);
}

function fmt(dateStr: string) {
  return new Date(dateStr).getFullYear().toString();
}

export default function PositionChart({ data, color = "#e85d4a" }: Props) {
  const chartData = data
    .filter((p) => p.frequency > 0)
    .map((p) => ({
      year: fmt(p.meeting_date),
      priority: priorityScore(p),
      title: p.title_zh,
      posLabel:
        p.first_char_position != null && p.doc_word_count
          ? `${Math.round((p.first_char_position / p.doc_word_count) * 100)}% into doc`
          : "unknown",
    }));

  if (chartData.every((d) => d.priority == null)) {
    return (
      <p className="text-sm py-8 text-center" style={{ color: "var(--muted)" }}>
        Position data not available — re-ingest documents to populate.
      </p>
    );
  }

  return (
    <div>
      <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
        100 = mentioned in the opening paragraph · 0 = mentioned only near the end.
        A rising trend means the government is foregrounding this term earlier in the document.
      </p>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3a" />
          <XAxis dataKey="year" tick={{ fill: "#64748b", fontSize: 11 }} tickLine={false} />
          <YAxis
            tick={{ fill: "#64748b", fontSize: 11 }}
            tickLine={false}
            domain={[0, 100]}
            tickFormatter={(v) => `${v}`}
          />
          <Tooltip
            contentStyle={{ background: "#1a1d27", border: "1px solid #2a2d3a", borderRadius: 8 }}
            labelStyle={{ color: "#e2e8f0", marginBottom: 4 }}
            itemStyle={{ color }}
            formatter={(val, _, props) => [
              `${val} / 100  (${(props as { payload?: { posLabel?: string } })?.payload?.posLabel ?? ""})`,
              "Priority score",
            ]}
            labelFormatter={(_, payload) => payload?.[0]?.payload?.title ?? ""}
          />
          <ReferenceLine y={50} stroke="#2a2d3a" strokeDasharray="4 4" label={{ value: "midpoint", fill: "#64748b", fontSize: 10, position: "right" }} />
          <Line
            type="monotone"
            dataKey="priority"
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
