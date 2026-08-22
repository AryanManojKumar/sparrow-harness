const evidenceSources = [
  "AWS",
  "GitHub",
  "Okta",
  "Google Cloud",
  "Datadog",
  "Snowflake",
];

export default function LogoWall() {
  return (
    <section
      className="bg-background py-20 md:py-28"
      aria-labelledby="evidence-sources-caption"
    >
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <div className="space-y-8 md:space-y-10">
          <p
            id="evidence-sources-caption"
            className="text-center font-body text-sm font-normal leading-5 text-muted-foreground"
          >
            Evidence sources used in continuous SOC 2 monitoring
          </p>

          <ul
            className="grid grid-cols-3 items-center gap-6 md:grid-cols-6 md:gap-8"
            role="list"
          >
            {evidenceSources.map((source) => (
              <li
                key={source}
                className="flex min-w-0 items-center justify-center text-center"
              >
                <span className="whitespace-nowrap font-display text-2xl font-semibold leading-[1.1] tracking-[-0.01em] text-foreground">
                  {source}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
