/**
 * Better Auth – zentrale Konfiguration der Badminton-Inhouse-Liga.
 *
 * Konfiguriert:
 *  - Login-Adapter über Drizzle/pg für PostgreSQL (compose.dev.yml, PORT 5432)
 *  - E-Mail + Passwort als einziger Provider
 *  - Öffentliche Registrierung explizit blockiert (`disableSignUp`)
 *  - Rate-Limit aktiviert
 *  - Zusatzfelder (additionalFields) aus Spec §5 / T003:
 *    display_name, is_active, role, rating_singles, rating_doubles
 */

import { betterAuth } from "better-auth";
import { drizzleAdapter } from "@better-auth/drizzle-adapter";

import { pool } from "./db";
import * as schema from "./db/schema";

export const auth = betterAuth({
  // ── Datenbank-Adapter: DrizzleORM mit node-postgres-Pool ──────
  adapter: drizzleAdapter(pool, {
    provider: "pg",
    schema,
  }),

  // ── E-Mail + Passwort aktivieren; Public Signup blockieren ────
  emailAndPassword: {
    enabled: true,
    disableSignUp: true,
  },

  // ── Session-Verwaltung ───────────────────────────────────────
  session: {
    expiresIn: 30 * 24 * 60 * 60, // 30 Tage
  },

  // ── Rate-Limit gegen brute-force ─────────────────────────────
  rateLimit: {
    enabled: true,
    window: 60,  // Sekunden
    max: 100,   // maximale Requests pro Fenster
  },

  // ── Sicherheits-Hashing-Einstellungen ────────────────────────
  advanced: {
    useSecureCookies: process.env.NODE_ENV === "production",
  },

  // ── Zusatzfelder für die `users`-Tabelle (Spec §5 / T003) ───
  databaseOptions: {
    additionalFields: {
      display_name: { type: "string", required: true, defaultValue: "" },
      is_active: { type: "boolean", required: true, defaultValue: true },
      role: {
        type: "string",
        required: true,
        defaultValue: "player",
      },
      rating_singles: { type: "number", required: true, defaultValue: 1000 },
      rating_doubles: { type: "number", required: true, defaultValue: 1000 },
    },
  },
});

export default auth;
