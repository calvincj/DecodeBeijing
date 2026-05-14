"use client";

import { useEffect, useState } from "react";

export default function ThemeToggle() {
  const [dark, setDark] = useState(true);

  useEffect(() => {
    const saved = localStorage.getItem("theme");
    const isDark = saved ? saved === "dark" : true;
    setDark(isDark);
    document.documentElement.setAttribute("data-theme", isDark ? "dark" : "light");
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    const theme = next ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }

  return (
    <button
      onClick={toggle}
      title={dark ? "Switch to light mode" : "Switch to dark mode"}
      style={{
        marginLeft: "auto",
        background: "none",
        border: "1px solid var(--border)",
        borderRadius: 6,
        padding: "3px 8px",
        cursor: "pointer",
        color: "var(--muted)",
        fontSize: "0.85rem",
        lineHeight: 1,
      }}
    >
      {dark ? "☀" : "☾"}
    </button>
  );
}
