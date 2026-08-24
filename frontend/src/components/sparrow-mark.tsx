import { cn } from "@/lib/utils";

/**
 * The console's mark. One path, `currentColor` — no image request, no flash,
 * recolors with the theme for free. Lives centered above the prompt box until
 * the first keystroke, then leaves for the session (see PromptConsole).
 */
export function SparrowMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("text-foreground", className)}
      aria-hidden="true"
    >
      {/* tail */}
      <path d="M10 40 L22 34 L22 40 Z" fill="currentColor" />
      {/* body */}
      <ellipse cx="34" cy="36" rx="16" ry="12" fill="currentColor" />
      {/* head */}
      <circle cx="47" cy="24" r="9" fill="currentColor" />
      {/* beak */}
      <path d="M55 23 L61 25 L55 27 Z" fill="currentColor" />
      {/* eye */}
      <circle cx="49" cy="22" r="1.5" className="fill-background" />
      {/* legs */}
      <path
        d="M28 47 L26 54 M34 48 L34 55"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}
