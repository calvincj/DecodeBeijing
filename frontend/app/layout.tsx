import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";
import ThemeToggle from "@/components/ThemeToggle";

export const metadata: Metadata = {
  title: "Decode Beijing",
  description: "Track language shifts in Chinese political documents",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <head>
        {/* Apply saved theme before first paint to avoid flash */}
        <script dangerouslySetInnerHTML={{ __html: `
          (function() {
            var t = localStorage.getItem('theme') || 'dark';
            document.documentElement.setAttribute('data-theme', t);
          })();
        `}} />
      </head>
      <body className="min-h-full flex flex-col" style={{ background: "var(--bg)", color: "var(--text)" }}>
        <nav style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)" }}
             className="px-6 py-3 flex items-center gap-6">
          <Link href="/" className="font-semibold text-lg tracking-tight">
            Decode Beijing <span style={{ color: "var(--accent)" }}>解码北京</span>
          </Link>
          <Link href="/" style={{ color: "var(--muted)" }} className="text-sm hover:opacity-80 transition-opacity">
            Terms
          </Link>
          <Link href="/documents" style={{ color: "var(--muted)" }} className="text-sm hover:opacity-80 transition-opacity">
            Documents
          </Link>
          <Link href="/compare" style={{ color: "var(--muted)" }} className="text-sm hover:opacity-80 transition-opacity">
            Compare
          </Link>
          <Link href="/candidates" style={{ color: "var(--muted)" }} className="text-sm hover:opacity-80 transition-opacity">
            Signals
          </Link>
          <ThemeToggle />
        </nav>
        <main className="flex-1 p-6">{children}</main>
      </body>
    </html>
  );
}
