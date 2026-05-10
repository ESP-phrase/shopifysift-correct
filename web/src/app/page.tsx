import { cookies } from "next/headers";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/auth";
import { loadResults, topCounts } from "@/lib/results";
import ResultsTable from "@/components/ResultsTable";
import { Wordmark } from "@/components/Logo";

async function getUser(): Promise<string | null> {
  const c = await cookies();
  const token = c.get(SESSION_COOKIE)?.value;
  if (!token) return null;
  const session = await verifySessionToken(token);
  return session?.user ?? null;
}

export default async function DashboardPage() {
  const [user, rows] = await Promise.all([getUser(), loadResults()]);

  const uniqueRepos = new Set(rows.map((r) => r.repo)).size;
  const uniqueQueries = new Set(rows.map((r) => r.query)).size;
  const topQueries = topCounts(rows, "query", 10);
  const topRepos = topCounts(rows, "repo", 10);

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_50%_30%_at_0%_100%,rgba(255,87,34,0.10),transparent_60%),radial-gradient(ellipse_50%_30%_at_100%_0%,rgba(255,87,34,0.06),transparent_60%)]" />
      <div className="relative mx-auto max-w-7xl px-6 py-8">
        <header className="mb-8 flex items-center justify-between">
          <Wordmark size={32} />
          <div className="flex items-center gap-4 text-sm">
            <span className="text-neutral-400">{user ?? ""}</span>
            <form action="/api/logout" method="POST">
              <button
                type="submit"
                className="text-orange-500 hover:underline"
              >
                Log out
              </button>
            </form>
          </div>
        </header>

        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="mt-1 mb-6 text-sm text-neutral-400">
          {rows.length} results loaded from{" "}
          <span className="font-mono">data/results.json</span>
        </p>

        <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          <Stat label="Total hits" value={rows.length} />
          <Stat label="Unique repos" value={uniqueRepos} />
          <Stat label="Queries" value={uniqueQueries} />
          <Stat label="Source" value="results.json" mono />
        </div>

        <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          <TopList title="Top queries" entries={topQueries} mono />
          <TopList title="Top repos" entries={topRepos} mono />
        </div>

        <ResultsTable rows={rows} />
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  mono,
}: {
  label: string;
  value: number | string;
  mono?: boolean;
}) {
  return (
    <div className="rounded-xl border border-neutral-900 bg-neutral-950 p-3.5">
      <div className="text-[11px] uppercase tracking-[0.1em] text-neutral-400">
        {label}
      </div>
      <div
        className={`mt-1 text-2xl font-semibold ${mono ? "font-mono text-sm" : ""}`}
      >
        {value}
      </div>
    </div>
  );
}

function TopList({
  title,
  entries,
  mono,
}: {
  title: string;
  entries: [string, number][];
  mono?: boolean;
}) {
  return (
    <div className="rounded-xl border border-neutral-900 bg-neutral-950 p-4">
      <h2 className="mb-3 text-xs uppercase tracking-[0.1em] text-neutral-400">
        {title}
      </h2>
      {entries.length === 0 ? (
        <div className="text-sm text-neutral-500">No data yet.</div>
      ) : (
        <ol className="list-decimal space-y-1 pl-5 text-sm text-neutral-400">
          {entries.map(([k, v]) => (
            <li key={k}>
              <span className="text-white">{v}</span> ·{" "}
              <span className={mono ? "font-mono text-xs" : ""}>{k}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
