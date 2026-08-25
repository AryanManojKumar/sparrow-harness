import type { Metadata } from "next";
import "./globals.css";

import { CloudField } from "@/components/cloud-field";
import { PointerGlow } from "@/components/pointer-glow";

export const metadata: Metadata = {
  title: "sparrow",
  description: "Build a business website from a brief and real material.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="console-sky min-h-screen antialiased">
        <CloudField />
        <PointerGlow />
        <div className="console-stars" aria-hidden="true" />
        {children}
      </body>
    </html>
  );
}
