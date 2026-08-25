import type { Metadata } from "next";
import "./globals.css";
import { cn } from "@/lib/utils";


// Per project — written by `builder` from `brief` + `content`.
// Title <60 chars, description <160 chars, both carrying the primary keyword.
export const metadata: Metadata = {
  title: "",
  description: "",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // Font families are bound by `sparrow tokens` from the design system.
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
