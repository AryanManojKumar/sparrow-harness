/**
 * Stand-in for `GET /runs/{id}/preview/*`, which will eventually serve the
 * real static export out of the run's workspace (see backend/README.md).
 * Until that exists, this is what the console's iframe points at — a real
 * same-origin page, so the preview mechanism (embedded iframe, device
 * toggle, refresh) is exercised end to end before there's a real site to
 * point it at.
 *
 * Deliberately undoes the console's dark chrome: a generated site should
 * not look like the harness that built it.
 */
export default function MockPreview() {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      <header className="flex items-center justify-between border-b border-slate-200 px-8 py-5">
        <span className="text-sm font-semibold tracking-tight">Ledgerline</span>
        <nav className="hidden gap-6 text-sm text-slate-600 sm:flex">
          <span>Product</span>
          <span>Pricing</span>
          <span>Docs</span>
        </nav>
        <button className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white">
          Get started
        </button>
      </header>

      <section className="mx-auto flex max-w-3xl flex-col items-center px-6 py-24 text-center">
        <span className="mb-4 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
          Now in preview
        </span>
        <h1 className="text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
          Close the books in hours, not weeks
        </h1>
        <p className="mt-4 max-w-xl text-slate-600">
          Ledgerline reconciles every ledger overnight and flags what needs a human
          before your team logs on.
        </p>
        <div className="mt-8 flex gap-3">
          <button className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white">
            Start free trial
          </button>
          <button className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700">
            Book a demo
          </button>
        </div>
      </section>

      <section className="mx-auto grid max-w-4xl grid-cols-1 gap-6 px-6 pb-24 sm:grid-cols-3">
        {["Auto-reconciliation", "Audit trail", "SOC 2 ready"].map((f) => (
          <div key={f} className="rounded-xl border border-slate-200 p-5">
            <div className="mb-3 size-8 rounded-lg bg-slate-100" />
            <p className="text-sm font-medium text-slate-900">{f}</p>
            <p className="mt-1 text-sm text-slate-500">
              Built for finance teams who close the books every month.
            </p>
          </div>
        ))}
      </section>

      <footer className="border-t border-slate-200 px-8 py-6 text-center text-xs text-slate-400">
        Ledgerline · placeholder preview, not a real deploy
      </footer>
    </div>
  );
}
