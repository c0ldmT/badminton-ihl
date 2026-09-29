/**
 * Login-Seite /login – Mobile-first Formular für E-Mail + Passwort.
 *
 * Authentifizierung erfolgt über Better Auth (API Catch-All unter
 * `/api/auth/[...all]`). Die Seite ist absichtlich eine Server Component:
 * Sie rendert initial leer, der Client nimmt Kontakt mit der API auf.
 */

"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch("/api/auth/sign-in/email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        throw new Error("Anmeldung fehlgeschlagen.");
      }

      // Success: Better Auth setzt das Session-Cookie in der Response.
      router.push("/");
    } catch (_err: unknown) {
      setError(
        _err instanceof Error
          ? _err.message || "Anmeldung fehlgeschlagen."
          : "Anmeldung fehlgeschlagen.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-md p-6">
      <h1 className="mb-6 text-2xl font-bold text-center">Anmelden</h1>

      {error && (
        <div className="mb-4 rounded border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} method="post" className="space-y-4">
        <div>
          <label htmlFor="email" className="mb-1 block text-sm font-medium">
            E-Mail
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            aria-label="E-Mail-Adresse"
            placeholder="Sie@email.de"
            maxLength={254}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-gray-300 bg-white px-4 min-h-[48px] text-lg leading-relaxed focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none"
          />
        </div>

        <div>
          <label htmlFor="password" className="mb-1 block text-sm font-medium">
            Passwort
          </label>
          <input
            id="password"
            type="password"
            required
            autoComplete="current-password"
            aria-label="Passwort"
            minLength={8}
            maxLength={254}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-gray-300 bg-white px-4 min-h-[48px] text-lg leading-relaxed focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-blue-600 px-6 py-3 min-h-[48px] text-lg font-semibold text-white hover:bg-blue-700 focus:ring-2 focus:ring-blue-300 outline-none disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Anmeldung…" : "Anmelden"}
        </button>
      </form>

      <p className="mt-6 text-center text-xs text-gray-400">
        Nur f�r eingeladene Mitglieder.
      </p>
    </main>
  );
}
