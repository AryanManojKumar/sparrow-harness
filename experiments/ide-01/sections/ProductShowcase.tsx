export default function ProductShowcase() {
  const diffRows = [
    {
      oldLine: "41",
      newLine: "41",
      marker: " ",
      content: "export async function authorize(request: Request) {",
      className: "bg-card text-foreground",
    },
    {
      oldLine: "42",
      newLine: "",
      marker: "−",
      content: "  const token = request.headers.get('authorization');",
      className: "bg-muted text-muted-foreground",
    },
    {
      oldLine: "",
      newLine: "42",
      marker: "+",
      content: "  const token = readBearerToken(request.headers);",
      className: "bg-background text-primary",
    },
    {
      oldLine: "",
      newLine: "43",
      marker: "+",
      content: "  const requestId = request.headers.get('x-request-id');",
      className: "bg-background text-primary",
    },
    {
      oldLine: "43",
      newLine: "44",
      marker: " ",
      content: "  if (!token) {",
      className: "bg-card text-foreground",
    },
    {
      oldLine: "44",
      newLine: "45",
      marker: " ",
      content: "    throw new UnauthorizedError({ requestId });",
      className: "bg-card text-foreground",
    },
    {
      oldLine: "45",
      newLine: "46",
      marker: " ",
      content: "  }",
      className: "bg-card text-foreground",
    },
    {
      oldLine: "",
      newLine: "47",
      marker: "+",
      content: "  return verifyToken(token, { requestId });",
      className: "bg-background text-primary",
    },
    {
      oldLine: "46",
      newLine: "",
      marker: "−",
      content: "  return verifyToken(token);",
      className: "bg-muted text-muted-foreground",
    },
    {
      oldLine: "47",
      newLine: "48",
      marker: " ",
      content: "}",
      className: "bg-card text-foreground",
    },
  ];

  return (
    <section
      className="bg-background py-20 md:py-28 lg:py-32"
      aria-labelledby="product-showcase-heading"
    >
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="space-y-8 md:space-y-10">
          <header className="max-w-4xl space-y-3">
            <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
              Product capture / review packet
            </p>
            <h2
              id="product-showcase-heading"
              className="font-display text-3xl font-semibold leading-[1.02] tracking-[-0.035em] text-foreground md:text-5xl"
            >
              One shared plan. A fleet of diffs you can still review.
            </h2>
            <p className="max-w-3xl font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
              Plan entries are assigned to named runs, each run records its
              touched files and commit, and every proposed change waits in a
              file-level diff with an explicit review checkpoint.
            </p>
          </header>

          <figure className="space-y-3">
            <div className="overflow-hidden rounded-md border border-border bg-card shadow-[0_2px_0_0_oklch(0.805_0.032_235)]">
              <div className="flex flex-col justify-between gap-5 border-b border-border bg-muted p-5 md:flex-row md:items-center md:gap-8">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                    northstar/api
                  </span>
                  <span className="text-muted-foreground" aria-hidden="true">
                    /
                  </span>
                  <span className="font-mono text-xs font-medium leading-5 tracking-[0.1em] text-primary">
                    run/1842
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className="h-2 w-2 rounded-full bg-primary"
                    aria-hidden="true"
                  />
                  <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                    6 runs resolved
                  </span>
                  <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                    14 files
                  </span>
                  <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                    0 merged
                  </span>
                </div>
              </div>

              <div className="overflow-x-auto">
                <div className="min-w-[880px]">
                  <div className="grid grid-cols-12 border-b border-border bg-card">
                    <div className="col-span-4 border-r border-border p-5">
                      <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                        01 / Plan
                      </p>
                    </div>
                    <div className="col-span-3 border-r border-border p-5">
                      <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                        02 / Run
                      </p>
                    </div>
                    <div className="col-span-5 p-5">
                      <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                        03 / Review
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-12">
                    <div className="col-span-4 border-r border-border bg-card p-5">
                      <div className="space-y-3">
                        <div className="border-l-2 border-primary bg-background p-5">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                              PLAN-14
                            </span>
                            <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                              assigned
                            </span>
                          </div>
                          <p className="font-body text-sm font-normal leading-6 text-foreground">
                            Propagate request IDs through authorization errors.
                          </p>
                          <p className="font-mono text-xs font-medium leading-5 tracking-[0.1em] text-muted-foreground">
                            scope: packages/api/src/auth/*
                          </p>
                        </div>

                        <div className="border-l-2 border-border p-5">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                              PLAN-15
                            </span>
                            <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                              resolved
                            </span>
                          </div>
                          <p className="font-body text-sm font-normal leading-6 text-foreground">
                            Add coverage for missing and malformed bearer
                            tokens.
                          </p>
                        </div>

                        <div className="border-l-2 border-border p-5">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                              PLAN-16
                            </span>
                            <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                              resolved
                            </span>
                          </div>
                          <p className="font-body text-sm font-normal leading-6 text-foreground">
                            Update the API error contract and generated schema.
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="col-span-3 border-r border-border bg-muted p-5">
                      <div className="space-y-3">
                        <div className="rounded-sm border border-primary bg-card p-5">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                              agent-02
                            </span>
                            <span
                              className="h-2 w-2 rounded-full bg-primary"
                              aria-label="Run complete"
                            />
                          </div>
                          <p className="font-mono text-xs font-medium leading-5 tracking-[0.1em] text-foreground">
                            run_1842.02
                          </p>
                          <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                            3 files · 1 commit
                          </p>
                          <p className="font-mono text-xs font-medium leading-5 tracking-[0.1em] text-muted-foreground">
                            7e3a19c
                          </p>
                        </div>

                        <div className="rounded-sm border border-border bg-card p-5">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                              agent-04
                            </span>
                            <span
                              className="h-2 w-2 rounded-full bg-primary"
                              aria-label="Run complete"
                            />
                          </div>
                          <p className="font-mono text-xs font-medium leading-5 tracking-[0.1em] text-foreground">
                            run_1842.04
                          </p>
                          <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                            2 test files · checks passed
                          </p>
                        </div>

                        <div className="rounded-sm border border-border bg-card p-5">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                              agent-05
                            </span>
                            <span
                              className="h-2 w-2 rounded-full bg-primary"
                              aria-label="Run complete"
                            />
                          </div>
                          <p className="font-mono text-xs font-medium leading-5 tracking-[0.1em] text-foreground">
                            run_1842.05
                          </p>
                          <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                            schema regenerated · no drift
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="col-span-5 bg-card">
                      <div className="flex items-start justify-between gap-5 border-b border-border p-5 md:gap-8">
                        <div className="space-y-3">
                          <p className="font-mono text-xs font-medium leading-5 tracking-[0.1em] text-foreground">
                            packages/api/src/auth/authorize.ts
                          </p>
                          <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                            7e3a19c · +4 −2
                          </p>
                        </div>
                        <div className="flex items-center gap-2 rounded-sm border border-accent bg-accent p-5">
                          <span
                            className="font-mono text-xs font-medium leading-5 text-foreground"
                            aria-hidden="true"
                          >
                            !
                          </span>
                          <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                            review required
                          </span>
                        </div>
                      </div>

                      <div className="border-l-2 border-primary">
                        <div className="border-b border-border bg-muted p-5">
                          <p className="font-mono text-xs font-medium leading-5 tracking-[0.1em] text-primary">
                            @@ -41,7 +41,8 @@ authorize(request)
                          </p>
                        </div>

                        <div>
                          {diffRows.map((row, index) => (
                            <div
                              key={`${row.oldLine}-${row.newLine}-${index}`}
                              className={`grid grid-cols-[3rem_3rem_1fr] border-b border-border ${row.className}`}
                            >
                              <span className="border-r border-border px-5 font-mono text-xs font-medium leading-5 tracking-[0.1em] text-muted-foreground">
                                {row.oldLine}
                              </span>
                              <span className="border-r border-border px-5 font-mono text-xs font-medium leading-5 tracking-[0.1em] text-muted-foreground">
                                {row.newLine}
                              </span>
                              <code className="whitespace-pre px-5 font-mono text-xs font-medium leading-5 tracking-[0.1em]">
                                {row.marker} {row.content}
                              </code>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="border-l-2 border-accent bg-muted p-5">
                        <div className="flex items-start gap-2">
                          <span
                            className="bg-accent px-5 font-mono text-xs font-medium leading-5 text-foreground"
                            aria-hidden="true"
                          >
                            !
                          </span>
                          <div className="space-y-3">
                            <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                              Reviewer checkpoint · unresolved
                            </p>
                            <p className="font-body text-sm font-normal leading-6 text-foreground">
                              Confirm that downstream audit events accept a
                              missing request ID before approving this hunk.
                            </p>
                            <p className="font-mono text-xs font-medium leading-5 tracking-[0.1em] text-muted-foreground">
                              owner: platform-reviewers · line 47
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between gap-5 border-t border-border bg-muted p-5 md:gap-8">
                    <p className="font-mono text-xs font-medium leading-5 tracking-[0.1em] text-muted-foreground">
                      harness review run_1842 --plan shared-plan.yaml
                    </p>
                    <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                      merge blocked · 1 checkpoint
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <figcaption className="font-body text-sm font-normal leading-6 text-muted-foreground">
              Review packet for{" "}
              <span className="font-mono text-xs font-medium leading-5 tracking-[0.1em] text-foreground">
                run_1842
              </span>
              : plan ownership, run provenance, commit identity, file-level
              changes, and the unresolved human decision remain attached to the
              same artifact.
            </figcaption>
          </figure>
        </div>
      </div>
    </section>
  );
}
