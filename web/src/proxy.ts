import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/auth";

const PROTECTED_PATHS = ["/", "/api/rows", "/api/run"];

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isProtected =
    PROTECTED_PATHS.some(
      (p) => pathname === p || pathname.startsWith(p + "/"),
    );
  if (!isProtected) return NextResponse.next();

  const token = request.cookies.get(SESSION_COOKIE)?.value;
  const session = token ? await verifySessionToken(token) : null;

  if (!session) {
    if (pathname.startsWith("/api/")) {
      return NextResponse.json({ error: "unauthorized" }, { status: 401 });
    }
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/api/rows/:path*", "/api/run/:path*"],
};
