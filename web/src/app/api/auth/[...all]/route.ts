/**
 * Catch-All API-Rout Handler für Better Auth.
 *
 * Weiterleitung aller auth-spezifischen Anfragen (GET / POST) an den von
 * betterAuth() erzeugten Router (`auth.handler`).  Next.js App Router braucht
 * explizite GET + POST Exporte – auch wenn wir beide gleich durchreichen.
 */

import { auth } from "@/server/auth";

export const GET = auth.handler;
export const POST = auth.handler;
