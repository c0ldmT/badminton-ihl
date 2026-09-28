#!/usr/bin/env bash
# Erzeugt das Web-Grundgerüst deterministisch (ersetzt Task T001 für die Agenten).
# Next.js 16 + TypeScript + Tailwind 4 + Drizzle/pg + Better Auth + Zod + Vitest.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
die() { printf '\033[31mFEHLER: %s\033[0m\n' "$*" >&2; exit 1; }

command -v node >/dev/null || die "Node.js fehlt (README Abschnitt 7.1)."
NODE_MAJOR=$(node -p 'process.versions.node.split(".")[0]')
NODE_MINOR=$(node -p 'process.versions.node.split(".")[1]')
{ [ "$NODE_MAJOR" -gt 20 ] || { [ "$NODE_MAJOR" -eq 20 ] && [ "$NODE_MINOR" -ge 9 ]; }; } \
  || die "Node.js >= 20.9 nötig (gefunden $(node -v)). Empfohlen: 22 LTS."
git rev-parse --show-toplevel >/dev/null 2>&1 || die "Kein Git-Repo. Erst README Abschnitt 5.1."
[ -e web ] && die "web/ existiert bereits – Bootstrap wurde schon ausgeführt."

export CI=1 NEXT_TELEMETRY_DISABLED=1 npm_config_fund=false npm_config_audit=false

say "Next.js-App anlegen (web/)"
npx --yes create-next-app@16 web \
  --ts --tailwind --eslint --app --src-dir --import-alias "@/*" \
  --use-npm --disable-git --yes

cd web
say "Abhängigkeiten installieren"
npm install --loglevel=error drizzle-orm pg better-auth zod
# create-next-app pinnt @types/node@^20, Vitest 5 verlangt >= 22 -> passend zu Node 22 LTS anheben
npm install --loglevel=error -D @types/node@^22 drizzle-kit @types/pg vitest tsx dotenv

say "npm-Skripte setzen"
npm pkg set \
  scripts.typecheck="next typegen && tsc --noEmit" \
  scripts.test="vitest run --passWithNoTests" \
  scripts.db:generate="drizzle-kit generate" \
  scripts.db:migrate="drizzle-kit migrate" \
  scripts.db:studio="drizzle-kit studio"

say "Konfiguration und Grundstruktur schreiben"
mkdir -p src/domain src/server/db/schema src/server/services src/components drizzle scripts

cat > vitest.config.ts <<'EOF'
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx", "scripts/**/*.test.ts"],
    exclude: ["**/*.db.test.ts", "node_modules/**"],
  },
});
EOF

cat > drizzle.config.ts <<'EOF'
import "dotenv/config";
import { defineConfig } from "drizzle-kit";

export default defineConfig({
  dialect: "postgresql",
  schema: "./src/server/db/schema/index.ts",
  out: "./drizzle",
  dbCredentials: { url: process.env.DATABASE_URL ?? "" },
  verbose: true,
});
EOF

cat > src/server/db/schema/index.ts <<'EOF'
// Zentrale Schema-Datei: jede Tabellen-Datei unter schema/ hier re-exportieren.
// Beispiel: export * from "./auth";
export {};
EOF

cat > src/server/db/index.ts <<'EOF'
import { drizzle } from "drizzle-orm/node-postgres";
import { Pool } from "pg";

import * as schema from "./schema";

// Ein Pool pro Prozess (auch bei Hot-Reload in der Entwicklung).
const globalForDb = globalThis as unknown as { pgPool?: Pool };

export const pool =
  globalForDb.pgPool ?? new Pool({ connectionString: process.env.DATABASE_URL });
if (process.env.NODE_ENV !== "production") globalForDb.pgPool = pool;

export const db = drizzle(pool, { schema });
export type Db = typeof db;
EOF

# Template nutzt next/font/google -> der Build lädt Schriften aus dem Internet.
# Für einen offline-fähigen, cloudfreien Build: System-Schriften + deutsches Grundlayout.
cat > src/app/layout.tsx <<'EOF'
import type { Metadata, Viewport } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Badminton-Liga",
  description: "Interne Badminton-Inhouse-Liga",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="de">
      <body className="min-h-dvh antialiased">{children}</body>
    </html>
  );
}
EOF

cat > src/app/globals.css <<'EOF'
@import "tailwindcss";

:root {
  --background: #ffffff;
  --foreground: #171717;
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --font-sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

@media (prefers-color-scheme: dark) {
  :root {
    --background: #0a0a0a;
    --foreground: #ededed;
  }
}

body {
  background: var(--background);
  color: var(--foreground);
  font-family: var(--font-sans);
}
EOF

cat > src/app/page.tsx <<'EOF'
export default function Home() {
  return (
    <main className="mx-auto max-w-md p-6">
      <h1 className="text-2xl font-bold">Badminton-Liga</h1>
      <p className="mt-2 text-sm opacity-70">
        Grundgerüst steht. Die Features entstehen Task für Task (siehe TASKS.md).
      </p>
    </main>
  );
}
EOF

cat > src/domain/README.md <<'EOF'
# domain/

Reine Fachlogik (Elo, Satzregeln, Match-Workflow). Keine Imports aus `next/*`,
der Datenbank oder Auth. Jede Datei bekommt einen Vitest-Test `<name>.test.ts`.
EOF

cat > .env.example <<'EOF'
# Dev-Datenbank aus compose.dev.yml
DATABASE_URL=postgres://liga:liga_dev_pw@127.0.0.1:5432/liga
# Better Auth (Secret: openssl rand -base64 32)
BETTER_AUTH_SECRET=bitte-ersetzen-mindestens-32-zeichen
BETTER_AUTH_URL=http://localhost:3000
# Mail (Dev: Mailpit aus compose.dev.yml)
SMTP_HOST=127.0.0.1
SMTP_PORT=1025
MAIL_FROM="Badminton-Liga <liga@localhost>"
EOF
SECRET=$(openssl rand -base64 32 2>/dev/null || node -e 'console.log(require("crypto").randomBytes(32).toString("base64"))')
sed "s|^BETTER_AUTH_SECRET=.*|BETTER_AUTH_SECRET=${SECRET}|" .env.example > .env
grep -q '^!.env.example' .gitignore || printf '\n# Vorlage darf ins Repo\n!.env.example\n' >> .gitignore

cd "$ROOT"
say "Prüf-Gate ausführen"
bash scripts/check.sh

say "T001 als erledigt markieren"
python3 autopilot/tasks.py set T001 done

cat <<'EOF'

Fertig. Nächste Schritte:
  docker compose -f compose.dev.yml up -d        # Dev-Datenbank starten
  git add -A && git commit -m "T001: Web-Grundgerüst (bootstrap)"
Danach den Autopiloten oder OpenCode starten (README Abschnitt 10/11).
EOF
