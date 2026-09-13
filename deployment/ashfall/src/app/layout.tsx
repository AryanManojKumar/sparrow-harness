import type { Metadata } from "next";
import "./globals.css";
import { IBM_Plex_Mono, Saira, Saira_Condensed } from "next/font/google";
const sairacondensed = Saira_Condensed({ subsets: ["latin"], display: "swap", weight: ["400", "500", "600", "700", "800"], variable: "--font-sairacondensed" });
const saira = Saira({ subsets: ["latin"], display: "swap", weight: ["400", "500", "600", "700", "800"], variable: "--font-saira" });
const ibmplexmono = IBM_Plex_Mono({ subsets: ["latin"], display: "swap", weight: ["400", "500", "600", "700"], variable: "--font-ibmplexmono" });
import { cn } from "@/lib/utils";


// Per project — written by `builder` from `brief` + `content`.
// Title <60 chars, description <160 chars, both carrying the primary keyword.
export const metadata: Metadata = {
  title: "ASHFALL — A first-person shooter set in a collapsing",
  description: "ASHFALL — A first-person shooter set in a collapsing volcanic city — a story campaign plus a 32-player extraction mode, launching on PlayStation 5, Xbox",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
        <html lang="en" className={cn("font-body", `${sairacondensed.variable} ${saira.variable} ${ibmplexmono.variable}`)}>
      <body>{children}</body>
    </html>
  );
}
