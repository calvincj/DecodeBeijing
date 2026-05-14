"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function CustomTermSearch() {
  const [value, setValue] = useState("");
  const router = useRouter();

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = value.trim();
    if (q) router.push(`/terms/custom?q=${encodeURIComponent(q)}`);
  }

  return (
    <section className="mb-8">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs font-medium px-2 py-0.5 rounded-full uppercase tracking-wider"
              style={{ background: "#64748b22", color: "#64748b" }}>
          custom
        </span>
      </div>
      <form onSubmit={submit} className="flex gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Search any term across all documents…"
          className="flex-1 text-sm px-3 py-2 rounded-lg outline-none"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            color: "var(--fg)",
          }}
        />
        <button
          type="submit"
          disabled={!value.trim()}
          className="text-sm px-4 py-2 rounded-lg font-medium"
          style={{
            background: value.trim() ? "#64748b33" : "var(--surface)",
            border: "1px solid var(--border)",
            color: value.trim() ? "var(--fg)" : "var(--muted)",
            cursor: value.trim() ? "pointer" : "default",
          }}
        >
          Search
        </button>
      </form>
    </section>
  );
}
