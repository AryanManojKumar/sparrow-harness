import type { Metadata } from "next";
import "./globals.css";
import { Chakra_Petch, IBM_Plex_Mono, Manrope } from "next/font/google";
const chakrapetch = Chakra_Petch({ subsets: ["latin"], display: "swap", weight: ["400", "500", "600", "700"], variable: "--font-chakrapetch" });
const manrope = Manrope({ subsets: ["latin"], display: "swap", weight: ["400", "500", "600", "700"], variable: "--font-manrope" });
const ibmplexmono = IBM_Plex_Mono({ subsets: ["latin"], display: "swap", weight: ["400", "500", "600", "700"], variable: "--font-ibmplexmono" });
import { cn } from "@/lib/utils";


// Per project — written by `builder` from `brief` + `content`.
// Title <60 chars, description <160 chars, both carrying the primary keyword.
export const metadata: Metadata = {
  title: "Meridian — A real-time engine for AAA game production",
  description: "Meridian — A real-time engine for AAA game production — streaming open worlds, virtualized geometry, and a physically based renderer that ships on console",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
        <html lang="en" className={cn("font-body", `${chakrapetch.variable} ${manrope.variable} ${ibmplexmono.variable}`)}>
      <body>{children}</body>
    </html>
  );
}
