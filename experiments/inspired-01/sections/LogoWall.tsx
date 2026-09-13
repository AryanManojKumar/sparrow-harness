const logos = ["Ramp", "Brex", "Mercury", "Column", "Lithic", "Unit"];

export default function LogoWall() {
  return (
    <section
      aria-labelledby="logo-wall-caption"
      className="bg-muted py-20"
    >
      <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-10">
        <div className="space-y-8 md:space-y-10">
          <p
            id="logo-wall-caption"
            className="text-center font-body text-sm font-normal leading-6 text-muted-foreground"
          >
            SOC 2 operations for fintech infrastructure teams
          </p>

          <ul
            aria-label="Fintech teams"
            className="grid grid-cols-3 items-center gap-5 md:grid-cols-6 md:gap-8"
          >
            {logos.map((logo) => (
              <li
                key={logo}
                className="text-center font-display text-2xl font-semibold leading-tight tracking-[-0.015em] text-foreground md:text-3xl"
              >
                {logo}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
