const evidenceSources = [
  "AWS",
  "GitHub",
  "Okta",
  "GCP",
  "Datadog",
  "Snowflake",
];

export default function LogoWall() {
  return (
    <section
      className="bg-background py-24 md:py-32"
      aria-labelledby="evidence-sources-caption"
    >
      <div className="mx-auto max-w-6xl px-6">
        <div className="space-y-8">
          <p
            id="evidence-sources-caption"
            className="text-center text-sm leading-normal text-muted-foreground"
          >
            SOC 2 evidence sources
          </p>

          <ul className="grid grid-cols-3 gap-8 md:grid-cols-6">
            {evidenceSources.map((source) => (
              <li
                key={source}
                className="flex items-center justify-center text-center text-xl font-medium leading-snug text-foreground"
              >
                {source}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
