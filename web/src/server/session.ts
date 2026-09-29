/**
 * Session-Helfer für die Badminton-Inhouse-Liga.
 *
 * Liest serverseitig (Server Components / Server Actions) die von Better Auth
 * gesetzte Session-Cookie aus dem aktuellen Request und gibt den User-Payload
 * sowie eine Rollen-Prüfung.
 */

import { auth } from "./auth";

// Typisierte Session + User, wie sie nach dem Login mit den additional_fields
// zurückgegeben wird ─ abgeleitet der DB-Schema-Felder aus T003/Spec §5.
export type User = {
  id: string;
  email: string;
  emailVerified: boolean;
  name: string | null;
  image: string | null;
  display_name: string;
  is_active: boolean;
  role: "player" | "admin";
  rating_singles: number;
  rating_doubles: number;
};

export type Session = {
  id: string;
  userId: string;
  expiresAt: Date;
  token: string;
  ipAddress?: string | null;
  userAgent?: string | null;
};

export type UserPayload = User & { session: Session };

// Interne Types für Adapter-Zugriff (DB-Spalten als Rows)
type SessionRow = {
  id: string;
  userId: string;
  expiresAt: Date | string;
  token: string;
  ipAddress?: string | null;
  userAgent?: string | null;
};

type UserRow = {
  id: string;
  email: string;
  emailVerified: boolean;
  name: string | null;
  image: string | null;
  display_name?: string;
  is_active?: unknown;
  role?: unknown;
  rating_singles?: unknown;
  rating_doubles?: unknown;
};

export interface Adapter {
  findOne<T>(data: { table: string; where: unknown[] }): Promise<T | null>;
}

// Minimaler Cookie-Store-Typ für den dynamischen Import von next/headers.
export interface ReadonlyCookieStore {
  get(name: string): { value: string } | undefined;
}

// =====================================================================
// getCurrentUser() – serverseitiger Session-Reader
// =====================================================================

/**
 * Liest die aktuelle Session.
 *
 * - Im echten Server-Kontext (keine args) wird der Cookie aus `next/headers`
 *   gelesen, per Adapter validiert und ein UserPayload aufgebaut.
 * - In Unit-Tests kann über den 1. Parameter ein gemockter Payload gesetzt
 *   werden — so testen wir ohne DB & Next.js-Laufzeit.
 */
export async function getCurrentUser(
  mock?: UserPayload | null,
): Promise<UserPayload | null> {
  // ── Test-Pfad ────────────────────────────────────────────────
  if (mock != null) {
    return mock;
  }

  // Kein gültiger Mock: entweder null (→ keine Session) oder undefined
  // (→ Server-Routine). In Tests ohne Next.js-Umgebung fangen wir das
  // bei Bedarf später via requireUser / requireAdmin ab.

  // ── Server-Kontext ───────────────────────────────────────────

  let cookieStore: ReadonlyCookieStore | null = null;

  try {
    const { cookies } = await import("next/headers");
    cookieStore = (await cookies()) as ReadonlyCookieStore;
  } catch {
    // Nicht in einem Request-Kontext (z. B. Unit-Tests ohne Mock).
    return null;
  }

  if (!cookieStore) {
    return null;
  }

  // Better Auth nutzt standardmäßig "better-auth.session_token".
  const sessionCookieName = "better-auth.session_token";

  const sessionToken = cookieStore.get(sessionCookieName)?.value;
  if (!sessionToken) {
    return null;
  }

  // über den Drizzle-Adapter die DB-Sitzung nachschauen
  try {
    const ctx = await auth.$context;
    // Adapter casten — DBAdapter ist komplexer generischer Schnittstellentyp,
    // der nicht direkt mit AdapterFindOne overlaps. Deswegen: unknown als Zwischenschritt.
    const adapter2 = (ctx.adapter as unknown as Adapter | undefined);
    if (!adapter2) return null;

    const dbSession = await adapter2.findOne<SessionRow | null>({
      table: "session",
      where: [{ field: "token", value: sessionToken }],
    });
    if (!dbSession || !dbSession.userId) return null;

    const dbUser = await adapter2.findOne<UserRow | null>({
      table: "users",
      where: [{ field: "id", value: dbSession.userId }],
    });
    if (!dbUser) return null;

    return {
      id: dbUser.id,
      email: dbUser.email,
      emailVerified: dbUser.emailVerified,
      name: dbUser.name ?? null,
      image: dbUser.image ?? null,
      display_name: (dbUser.display_name ?? "") as string,
      is_active: Boolean(dbUser.is_active ?? true),
      role: (dbUser.role as "player" | "admin") ?? "player",
      rating_singles: Number(dbUser.rating_singles) || 1000,
      rating_doubles: Number(dbUser.rating_doubles) || 1000,
      session: {
        id: dbSession.id,
        userId: dbSession.userId,
        expiresAt: new Date(dbSession.expiresAt),
        token: sessionToken,
        ipAddress: dbSession.ipAddress ?? null,
        userAgent: dbSession.userAgent ?? null,
      },
    };
  } catch {
    // Bei DB-Fehlern keine Autorisierung gewähren.
    return null;
  }
}

// =====================================================================
// requireUser – serverseitig zwingend authentifizierte Anfrage
// =====================================================================

export async function requireUser(
  mock?: UserPayload | null,
): Promise<UserPayload> {
  const user = await getCurrentUser(mock);
  if (!user) {
    throw Object.assign(new Error("Unauthorized"), { status: 401 as const });
  }
  return user;
}

// =====================================================================
// requireAdmin – Rolle "admin" zwingend erforderlich
// =====================================================================

/**
 * Prüft serverseitig, ob der aktuelle User die Rolle `"admin"` hat.
 *
 * Wirft bei fehlender Anmeldung → 401.
 * Wirft wenn role !== "admin"  → 403.
 */
export async function requireAdmin(
  mock?: UserPayload | null,
): Promise<UserPayload> {
  const user = await requireUser(mock);

  if (user.role !== "admin") {
    throw Object.assign(new Error("Forbidden"), { status: 403 as const });
  }

  return user;
}
