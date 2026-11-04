import { NextResponse, type NextRequest } from "next/server";

const COOKIE = "__Host-sb_sid";

export function middleware(request: NextRequest) {
  const hasSession = request.cookies.has(COOKIE);
  if (hasSession) return NextResponse.next();

  const url = request.nextUrl.clone();
  const next = `${request.nextUrl.pathname}${request.nextUrl.search}`;
  url.pathname = "/masuk";
  url.search = "";
  url.searchParams.set("next", next);
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/app/:path*", "/ops/:path*"],
};