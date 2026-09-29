/**
 * proxy.ts – Access-Guard f�r die Badminton-Inhouse-Liga.
 *
 * Next.js 16 hat „middleware" durch „proxy" ersetzt. Diese Datei wird
 * f�r ALLE Requests ausgef�hrt (kein matcher), was bedeutet DASS statische
 * Dateien und API-Routen auch den Guard passieren – daher die Ausschl�sse
 * unten.
 *
 * Alle Anfragen ohne g�ltiges Session-Cookie werden auf /login weitergeleitet,
 * mit Ausnahme der explizit freigegebenen Pfade:
 *   /login            ‑ Anmeldung selbst
 *   /invite/*         ‑ Einladungstoken-Best�tigung (T004+)
 *   /reset-password/* ‑ Passwort-Zur�cksetzen (T007+)
 *   /api/*            ‑ Schnittstellen, besonders /api/auth/*
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/** Pfade, die immer erreichbar sein m�ssen */
const EXEMPT_PREFIXES = ["/login", "/invite/", "/reset-password/", "/api/"];

function isExempt(pathname: string): boolean {
  return EXEMPT_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

// Session-Cookie von Better Auth. F�r den Guard reicht eine einfache
// An-/Abwesenheitspr�fung – die eigentliche Signatur-Validierung nimmt
// `/api/auth/get-session` vor.
const SESSION_COOKIE = "better-auth.session_token";

export function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // 1. Exempt prüfen
  if (isExempt(pathname)) {
    return NextResponse.next();
  }

  // 2. Session-Cookie vorhanden?
  const sessionCookie = request.cookies.get(SESSION_COOKIE);
  if (!sessionCookie || !sessionCookie.value) {
    // Kein Cookie: zum Login leiten, aber die Destination im URL speichern
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Session vorhanden → Request durchlassen
  return NextResponse.next();
}
