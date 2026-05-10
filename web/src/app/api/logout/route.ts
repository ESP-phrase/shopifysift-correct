import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/auth";

export async function POST(request: Request) {
  const res = NextResponse.redirect(new URL("/login", request.url), {
    status: 303,
  });
  res.cookies.delete(SESSION_COOKIE);
  return res;
}

export const GET = POST;
