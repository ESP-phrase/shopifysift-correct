import { NextResponse } from "next/server";
import { loadResults, type ResultRow } from "@/lib/results";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const q = (searchParams.get("q") ?? "").toLowerCase();
  const repo = (searchParams.get("repo") ?? "").toLowerCase();
  const path = (searchParams.get("path") ?? "").toLowerCase();

  const all = await loadResults();
  const match = (r: ResultRow) =>
    (!q || r.query.toLowerCase().includes(q)) &&
    (!repo || r.repo.toLowerCase().includes(repo)) &&
    (!path || r.path.toLowerCase().includes(path));

  return NextResponse.json(all.filter(match));
}
