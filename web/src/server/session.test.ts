/**
 * Unit-Tests für session.ts – SessionHelper getCurrentUser / requireAdmin.
 *
 * Alle Tests arbeiten mit gemocktem UserPayload, das direkt als Parameter
 * übergeben wird ─ kein laufender Next.js oder Datenbank nötig.
 */

import { describe, expect, test } from "vitest";

import type { UserPayload } from "./session";
import { getCurrentUser, requireAdmin, requireUser } from "./session";

// ─── Hilfsfunktion: ein gültiges Mock-Payload bauen ────────────────

function makeMockPayload(overrides?: Partial<UserPayload>): UserPayload {
  return {
    id: "user-123",
    email: "player@example.com",
    emailVerified: true,
    name: "Max Mustermann",
    image: null,
    display_name: "max",
    is_active: true,
    role: "player",
    rating_singles: 1200,
    rating_doubles: 1100,
    session: {
      id: "sess-abc",
      userId: "user-123",
      expiresAt: new Date(Date.now() + 86_400_000),
      token: "fake-token",
      ipAddress: null,
      userAgent: null,
    },
    ...overrides,
  };
}

// ====================================================================
// getCurrentUser
// ====================================================================

describe("getCurrentUser", () => {
  test("gibt den gemockten UserPayload unverändert zurück", async () => {
    const payload = makeMockPayload();
    const result = await getCurrentUser(payload);
    expect(result).toEqual(payload);
  });

  test("gibt null zurück wenn explizit null gemockt wird", async () => {
    const result = await getCurrentUser(null);
    expect(result).toBeNull();
  });

  test("verwendet Standardwerte bei teilweise gesetztem Mock", async () => {
    const payload = makeMockPayload({
      display_name: "testuser",
      is_active: true,
      role: "admin" as "player" | "admin",
      rating_singles: 1500,
      rating_doubles: 1400,
    });
    const result = await getCurrentUser(payload);
    expect(result).not.toBeNull();
    expect(result!.display_name).toBe("testuser");
    expect(result!.is_active).toBe(true);
    expect(result!.role).toBe("admin");
    expect(result!.rating_singles).toBe(1500);
    expect(result!.rating_doubles).toBe(1400);
  });
});

// ====================================================================
// requireUser
// ====================================================================

describe("requireUser", () => {
  test("gibt UserPayload zurück wenn gültiger Mock gesetzt ist", async () => {
    const payload = makeMockPayload({ role: "admin" });
    const result = await requireUser(payload);
    expect(result.id).toBe("user-123");
    expect(result.session.userId).toBe("user-123");
  });

  test("wirft Error wenn Mock null ist (keine Session)", async () => {
    await expect(requireUser(null)).rejects.toThrow("Unauthorized");
  });

  test("wirft Error wenn kein Parameter (undefined = kein Mock)", async () => {
    // Ohne gültigen Mock ist die "Session" leer → Error.
    const thrown = await requireUser().catch((e) => e);
    expect(thrown).toBeInstanceOf(Error);
    if (thrown instanceof Error) {
      expect(thrown.message).toBe("Unauthorized");
    }
  });
});

// ====================================================================
// requireAdmin
// ====================================================================

describe("requireAdmin", () => {
  test("erlaubt Admin-Sessions durch", async () => {
    const payload = makeMockPayload({ role: "admin" });
    const result = await requireAdmin(payload);
    expect(result.role).toBe("admin");
  });

  test("wirft Error bei Non-Admin Sessions (role !== \"admin\")", async () => {
    const payload = makeMockPayload({ role: "player" });
    const error = await requireAdmin(payload).catch((e) => e);

    expect(error).toBeInstanceOf(Error);
    if (error instanceof Error) {
      expect(error.message).toBe("Forbidden");
      // status-Property sollte als Error-extension vorhanden sein
      expect((error as unknown as Record<string, unknown>).status).toBe(403);
    }
  });

  test("wirft Error bei fehlender Session (kein Mock)", async () => {
    const thrown = await requireAdmin().catch((e) => e);
    expect(thrown).toBeInstanceOf(Error);
    if (thrown instanceof Error) {
      expect(thrown.message).toBe("Unauthorized");
      expect((thrown as unknown as Record<string, unknown>).status).toBe(401);
    }
  });

  test("verweigert Zugriff wenn Mock null ist", async () => {
    const thrown = await requireAdmin(null).catch((e) => e);
    expect(thrown).toBeInstanceOf(Error);
    if (thrown instanceof Error) {
      expect(thrown.message).toBe("Unauthorized");
    }
  });
});
