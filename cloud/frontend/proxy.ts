import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isProtectedRoute = createRouteMatcher(["/dashboard(.*)"]);

const clerkProtectedMiddleware = clerkMiddleware(async (auth, req) => {
  if (isProtectedRoute(req)) await auth.protect();
});

function e2eBypassMiddleware() {
  return NextResponse.next();
}

const middleware =
  process.env.SLATE_E2E_AUTH_BYPASS === "true"
    ? e2eBypassMiddleware
    : clerkProtectedMiddleware;

export default middleware;

export const config = {
  matcher: ["/((?!.*\\..*|_next).*)", "/", "/(api|trpc)(.*)"],
};
