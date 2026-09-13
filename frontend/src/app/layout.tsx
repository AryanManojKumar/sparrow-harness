import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "sparrow",
  description: "Build a business website from a brief and real material.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      {/* `console-sky` is a static background-image and costs nothing, so it
          stays global. The animated layers do not — see
          components/console-backdrop.tsx, which the home screen mounts and
          the workspace deliberately does not. */}
      <body className="console-sky min-h-screen antialiased">{children}</body>
    </html>
  );
}
