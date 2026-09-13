/** Shared URL helpers for the reference-sites input. */

const URL_RE = /https?:\/\/[^\s,)"'<>]+/g;

export function isHttpUrl(value: string): boolean {
  try {
    const u = new URL(value.trim());
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

export function hostnameOf(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

/** Every http(s) URL found in free text, trailing punctuation trimmed. */
export function extractUrls(text: string): string[] {
  const matches = text.match(URL_RE) ?? [];
  return matches.map((m) => m.replace(/[.,;:!?]+$/, ""));
}
