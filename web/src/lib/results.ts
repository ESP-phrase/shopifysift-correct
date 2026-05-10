import fs from "node:fs/promises";
import path from "node:path";

export type ResultRow = {
  query: string;
  repo: string;
  path: string;
  url: string;
  repo_url: string;
};

export async function loadResults(): Promise<ResultRow[]> {
  const file = path.join(process.cwd(), "data", "results.json");
  try {
    const raw = await fs.readFile(file, "utf-8");
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function topCounts(rows: ResultRow[], key: keyof ResultRow, n = 10) {
  const counts = new Map<string, number>();
  for (const r of rows) {
    counts.set(r[key], (counts.get(r[key]) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, n);
}
