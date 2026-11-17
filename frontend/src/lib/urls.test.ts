import { describe, expect, it } from "vitest";

import { extractUrls, hostnameOf, isHttpUrl } from "@/lib/urls";

describe("isHttpUrl", () => {
  it("isHttpUrl_fullHttpsUrl_true", () => {
    expect(isHttpUrl("https://crumbsandwhiskers.com")).toBe(true);
  });

  it("isHttpUrl_surroundingWhitespace_true", () => {
    expect(isHttpUrl("  https://example.com/path  ")).toBe(true);
  });

  // The home screen's "two full URLs" rule rests on this: a bare domain is
  // not enough for the scout to open.
  it("isHttpUrl_bareDomain_false", () => {
    expect(isHttpUrl("example.com")).toBe(false);
  });

  it("isHttpUrl_otherScheme_false", () => {
    expect(isHttpUrl("ftp://example.com")).toBe(false);
    expect(isHttpUrl("javascript:alert(1)")).toBe(false);
  });

  it("isHttpUrl_empty_false", () => {
    expect(isHttpUrl("")).toBe(false);
  });
});

describe("hostnameOf", () => {
  it("hostnameOf_url_returnsHost", () => {
    expect(hostnameOf("https://www.meowparlour.com/visit")).toBe("www.meowparlour.com");
  });

  it("hostnameOf_notAUrl_returnsInputUnchanged", () => {
    expect(hostnameOf("not a url")).toBe("not a url");
  });
});

describe("extractUrls", () => {
  it("extractUrls_prose_findsEachUrlWithTrailingPunctuationTrimmed", () => {
    const text = "Like https://a.com, and https://b.com/x. Also (https://c.com)!";
    expect(extractUrls(text)).toEqual(["https://a.com", "https://b.com/x", "https://c.com"]);
  });

  it("extractUrls_noUrls_empty", () => {
    expect(extractUrls("a cat café in Pune")).toEqual([]);
  });
});
