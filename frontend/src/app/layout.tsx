import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

// Self-hosted at build time and preloaded: no request to Google from the
// browser, and a size-adjusted fallback so the swap does not shift layout.
const sans = Geist({ subsets: ["latin"], variable: "--font-geist-sans" });
// Not preloaded: mono only sets small log lines and the spend chip, never the
// headline, and a high-priority preload put its 29 KB ahead of the page's LCP.
const mono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono", preload: false });

export const metadata: Metadata = {
  title: "sparrow",
  description: "Build a business website from a brief and real material.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`dark ${sans.variable} ${mono.variable}`}>
      {/* `console-sky` is a static background-image and costs nothing, so it
          stays global. The animated layers do not — see
          components/console-backdrop.tsx, which the home screen mounts and
          the workspace deliberately does not. */}
      <body className="console-sky min-h-screen antialiased">{children}</body>
    </html>
  );
}
