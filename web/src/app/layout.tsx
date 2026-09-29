import type { Metadata, Viewport } from "next";

import "./globals.css";
import LogoutButton from "@/components/LogoutButton";

export const metadata: Metadata = {
  title: "Badminton-Liga",
  description: "Interne Badminton-Inhouse-Liga",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="de">
      {/* Verhindert Suchmaschinen-Indexierung aller Seiten */}
      <meta name="robots" content="noindex,nofollow" />
      <body className="min-h-dvh antialiased">
        <LogoutButton />
        {children}
      </body>
    </html>
  );
}
