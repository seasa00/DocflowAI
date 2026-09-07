const foundationItems = [
  "Next.js, TypeScript, and Tailwind CSS",
  "FastAPI service with a database health check",
  "PostgreSQL running through Docker Compose",
];

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-4xl items-center px-6 py-16">
      <section className="w-full rounded-2xl border border-slate-200 bg-white p-8 shadow-sm sm:p-12">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-700">
          Sprint 1 foundation
        </p>
        <h1 className="mt-4 text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">
          DocFlow AI
        </h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">
          A foundation for converting unstructured documents into structured,
          reviewable data.
        </p>

        <div className="mt-10 rounded-xl bg-slate-50 p-6">
          <h2 className="text-base font-semibold text-slate-900">
            Available now
          </h2>
          <ul className="mt-4 space-y-3 text-slate-700">
            {foundationItems.map((item) => (
              <li className="flex items-center gap-3" key={item}>
                <span
                  aria-hidden="true"
                  className="h-2.5 w-2.5 rounded-full bg-emerald-500"
                />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </section>
    </main>
  );
}
