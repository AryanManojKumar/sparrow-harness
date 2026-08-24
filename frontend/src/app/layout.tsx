import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "sparrow",
  description: "Build a business website from a brief and real material.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="console-sky min-h-screen antialiased">{children}</body>
    </html>
  );
}
