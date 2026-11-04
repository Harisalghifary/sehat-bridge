import { NextResponse, type NextRequest } from "next/server";

const APP_COOKIE = "__Host-sb_sid";
const OPS_COOKIE = "__Host-sb_ops";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname === "/ops/masuk") return NextResponse.next();

  if (pathname.startsWith("/ops")) {
    if (request.cookies.has(OPS_COOKIE)) return NextResponse.next();
    const url = request.nextUrl.clone();
    url.pathname = "/ops/masuk";
    url.search = "";
    url.searchParams.set("next", `${pathname}${request.nextUrl.search}`);
    return NextResponse.redirect(url);
  }

  if (request.cookies.has(APP_COOKIE)) return NextResponse.next();

  const url = request.nextUrl.clone();
  url.pathname = "/masuk";
  url.search = "";
  url.searchParams.set("next", `${pathname}${request.nextUrl.search}`);
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/app/:path*", "/ops/:path*"],
};