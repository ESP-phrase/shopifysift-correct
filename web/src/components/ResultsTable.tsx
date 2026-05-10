"use client";

import { useMemo, useState } from "react";
import type { ResultRow } from "@/lib/results";

export default function ResultsTable({ rows }: { rows: ResultRow[] }) {
  const [q, setQ] = useState("");
  const [repo, setRepo] = useState("");
  const [path, setPath] = useState("");

  const filtered = useMemo(() => {
    const ql = q.toLowerCase();
    const rl = repo.toLowerCase();
    const pl = path.toLowerCase();
    return rows.filter(
      (r) =>
        (!ql || r.query.toLowerCase().includes(ql)) &&
        (!rl || r.repo.toLowerCase().includes(rl)) &&
        (!pl || r.path.toLowerCase().includes(pl)),
    );
  }, [rows, q, repo, path]);

  return (
    <div className="rounded-xl border border-neutral-900 bg-neutral-950 p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-xs uppercase tracking-[0.1em] text-neutral-400">
          Results
        </h2>
        <span className="rounded-full bg-orange-500/10 px-2.5 py-1 text-xs text-orange-500">
          {filtered.length === rows.length
            ? rows.length
            : `${filtered.length} / ${rows.length}`}
        </span>
      </div>
      <div className="mb-3 grid grid-cols-1 gap-2 md:grid-cols-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="filter by query…"
          className="rounded-md border border-neutral-800 bg-neutral-950 px-3 py-2 text-sm placeholder:text-neutral-600 focus:border-orange-500 focus:outline-none"
        />
        <input
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          placeholder="filter by repo…"
          className="rounded-md border border-neutral-800 bg-neutral-950 px-3 py-2 text-sm placeholder:text-neutral-600 focus:border-orange-500 focus:outline-none"
        />
        <input
          value={path}
          onChange={(e) => setPath(e.target.value)}
          placeholder="filter by path…"
          className="rounded-md border border-neutral-800 bg-neutral-950 px-3 py-2 text-sm placeholder:text-neutral-600 focus:border-orange-500 focus:outline-none"
        />
      </div>
      <div className="max-h-[600px] overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-neutral-950">
            <tr className="text-left text-xs uppercase tracking-[0.1em] text-neutral-400">
              <th className="border-b border-neutral-900 px-3 py-2 font-medium">
                Query
              </th>
              <th className="border-b border-neutral-900 px-3 py-2 font-medium">
                Repo
              </th>
              <th className="border-b border-neutral-900 px-3 py-2 font-medium">
                Path
              </th>
              <th className="border-b border-neutral-900 px-3 py-2 font-medium">
                Open
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td
                  colSpan={4}
                  className="px-3 py-8 text-center text-sm text-neutral-500"
                >
                  No results yet. Run the scraper locally and commit
                  data/results.json to populate.
                </td>
              </tr>
            ) : (
              filtered.map((r, i) => (
                <tr
                  key={`${r.repo}-${r.path}-${i}`}
                  className="hover:bg-orange-500/5"
                >
                  <td className="border-b border-neutral-900 px-3 py-2 font-mono text-xs">
                    {r.query}
                  </td>
                  <td className="border-b border-neutral-900 px-3 py-2">
                    <a
                      href={r.repo_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-orange-500 hover:underline"
                    >
                      {r.repo}
                    </a>
                  </td>
                  <td className="border-b border-neutral-900 px-3 py-2 font-mono text-xs">
                    {r.path}
                  </td>
                  <td className="border-b border-neutral-900 px-3 py-2">
                    <a
                      href={r.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-orange-500 hover:underline"
                    >
                      file →
                    </a>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
