"use client";

import { useRouter, usePathname } from "next/navigation";
import { useState, type FormEvent } from "react";

/**
 * Logout-Button
 *
 * POST an `/api/auth/sign-out`, danach zu /login.
 * Wird nur gerendert, wenn wir uns NICHT auf der Login-Seite befinden.
 */
export default function LogoutButton() {
  const pathname = usePathname();
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  // Keine Abmelde-Mogik auf der Login-Seite selbst
  if (pathname === "/login") return null;

  async function handleLogout(e: FormEvent) {
    e.preventDefault();
    setLoading(true);

    try {
      await fetch("/api/auth/sign-out", {
        method: "POST",
      });
    } catch {
      /* noop */
    } finally {
      router.push("/login");
    }
  }

  return (
    <div className="mx-auto mt-2 max-w-md px-6">
      <form onSubmit={handleLogout}>
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg border border-gray-300 bg-white py-3 min-h-[48px] text-center text-sm font-medium text-gray-700 hover:bg-gray-50 focus:ring-2 focus:ring-blue-200 outline-none disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Abmeldung…" : "Abmelden"}
        </button>
      </form>
    </div>
  );
}
