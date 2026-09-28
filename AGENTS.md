# AGENTS.md – Projektkontext: Badminton Inhouse-Liga

Gilt für alle Agenten. Kurz gehalten, weil diese Datei in jeden Prompt geladen wird.
Fachliche Quelle der Wahrheit: `docs/PROJECT_SPEC.md`. Arbeitsstand: `TASKS.md`.
Bei Widersprüchen gewinnt immer die Spec.

## Ziel
Interne, mobile-first Web-App (PWA) für eine geschlossene Badminton-Gruppe:
Einladungs-Login, schnelle Match-Erfassung (Einzel/Doppel), Vier-Augen-Bestätigung,
getrenntes Elo-Rating Einzel/Doppel, Ligatabellen. UI-Sprache: Deutsch.
Zugriff nur über Tailscale, kein öffentlicher Betrieb.

## Tech-Stack (nicht ohne Rücksprache ändern)
- Next.js 16 (App Router, TypeScript strict, Server Actions), Tailwind CSS 4
- PostgreSQL 17 (Dev: `compose.dev.yml`), Drizzle ORM + drizzle-kit, Treiber `pg`
- Auth: Better Auth (E-Mail + Passwort, Drizzle-Adapter, kein öffentlicher Signup)
- Validierung: Zod · Tests: Vitest
- Deployment später: Docker Compose, selbst gehostet

## Repo-Struktur
```
web/                       Next.js-App (alles App-bezogene liegt hier)
  src/app/                 Routen, Seiten, Server Actions (dünn!)
  src/components/          UI-Komponenten (keine Fachlogik)
  src/domain/              REINE Fachlogik: Elo, Satzregeln, Match-Workflow.
                           Keine Imports aus next/*, DB oder Auth. Jede Datei hat *.test.ts
  src/server/db/           Drizzle-Client (index.ts) und Schema (schema/*.ts)
  src/server/services/     DB-Zugriffe + Transaktionen, nutzen src/domain
  src/server/auth.ts       Better-Auth-Konfiguration
  drizzle/                 generierte Migrationen (committen, nie von Hand ändern)
scripts/check.sh           Prüf-Gate: typecheck, lint, test, build
```
Identifier/Code auf Englisch, UI-Texte und Kommentare auf Deutsch.

## Befehle
- Gesamtprüfung (vom Repo-Root): `bash scripts/check.sh`
- In `web/`: `npm run typecheck` · `npm run lint` · `npm test` · `npm run build`
- Migrationen: `npm run db:generate` dann `npm run db:migrate` (DB: `docker compose -f compose.dev.yml up -d`)

## Harte Regeln für Agenten
- Alle Befehle müssen nicht-interaktiv laufen. Verboten: `npm run dev`, `next dev`,
  Watch-Modi, `drizzle-kit push`, Befehle, die auf Eingaben warten.
- Kein `git commit/push/reset/checkout` – Commits macht der Mensch bzw. der Autopilot.
- Nicht ändern: `TASKS.md` (nur Planner), `AGENTS.md`, `docs/`, `scripts/`,
  `autopilot/`, `.opencode/`, `opencode.json`, `compose.dev.yml`.
- Keine Features außerhalb der Task. Unklarheit = Rückfrage, nicht raten.
- Schema-Änderungen nur in Tasks, die ausdrücklich Schema-Tasks sind.
- Rechte (wer darf was) immer serverseitig prüfen, nie nur in der UI.
- Keine neuen Abhängigkeiten zu Cloud-Diensten. Neue npm-Pakete nur, wenn die Task
  es erfordert, und im Abschlussbericht nennen.
- Next.js 16 weicht von älterem Wissen ab (z. B. `proxy.ts` statt `middleware.ts`):
  bei Zweifeln `web/AGENTS.md` und `web/node_modules/next/dist/docs/` lesen.

## Rollen
| Rolle | Aufgabe |
|---|---|
| `planner` | (interaktiv) wählt eine Task, delegiert, pflegt TASKS.md |
| `coder` | setzt genau eine Task um, prüft mit `scripts/check.sh` |
| `spec-reviewer` | nur: Akzeptanzkriterien erfüllt? Scope eingehalten? |
| `quality-reviewer` | nur: Bugs, Fehlerbehandlung, Sicherheit, Tests (blockiert nur bei echten Mängeln) |

## Definition of Done
Checks grün · Spec-Review PASS · Quality-Review PASS · Kernlogik hat Tests ·
UI-Tasks werden zusätzlich vom Menschen bei ~375 px Breite angesehen.
