# TASKS.md – Task-Board

Maschinenlesbar: Der Autopilot (`autopilot/`) und der `planner` lesen und schreiben diese
Datei. Bitte das Format beibehalten:

```
### <ID> · <Titel>
status: <open|done|blocked> | depends: <IDs, kommagetrennt, oder -> | spec: <Abschnitte>
<Beschreibung>
**Akzeptanz**
- ...
**Nicht im Scope**
- ...
```

Regeln: Es wird immer die erste `open`-Task genommen, deren `depends` alle `done` sind.
Tasks sind bewusst klein geschnitten (ein lokales Modell schafft kleine Schritte deutlich
zuverlässiger). Schema-Änderungen sind eigene Tasks. Blockierte Tasks bekommen eine
Zeile `> BLOCKED: ...` – zum Freigeben Grund klären, Zeile löschen, Status auf `open`.

## Backlog

### T001 · Web-Grundgerüst (per Skript, nicht durch Agenten)
status: done | depends: - | spec: 4
Wird deterministisch durch `bash scripts/bootstrap-web.sh` erzeugt (Next.js 16, Tailwind,
Drizzle, Better Auth, Vitest, npm-Skripte, `.env`). Das Skript setzt diese Task auf `done`.
**Akzeptanz**
- `web/` existiert, `bash scripts/check.sh` ist grün

### T002 · DB-Anbindung und Health-Check
status: done | depends: T001 | spec: 5
Drizzle-Client in `web/src/server/db/index.ts` nutzt `DATABASE_URL`. Route
`GET /api/health` liefert JSON `{ status: "ok", db: "up" | "down" }` und prüft die DB mit
`select 1`. Fehler der DB führen zu `db: "down"` und HTTP 503, nicht zu einem Absturz.
**Akzeptanz**
- `web/src/app/api/health/route.ts` existiert und behandelt DB-Fehler
- Hilfsfunktion für den DB-Check ist separat und hat einen Unit-Test (DB gemockt)
- checks grün
**Nicht im Scope**
- Schema-Tabellen, Auth

### T003 · Schema-Task: Better-Auth-Tabellen + Spieler-Zusatzfelder
status: done | depends: T002 | spec: 3.1, 5
Drizzle-Schema für die von Better Auth benötigten Tabellen (user, session, account,
verification) in `web/src/server/db/schema/auth.ts`. Die `user`-Tabelle ist die
Spieler-Tabelle aus Spec §5 und bekommt zusätzlich: `displayName` (text, not null),
`isActive` (bool, default true), `role` (text, default "player"; Werte "player"|"admin"),
`ratingSingles` und `ratingDoubles` (integer, default 1000). Migration generieren.
**Akzeptanz**
- Schema-Datei + generierte Migration unter `web/drizzle/`
- `npm run db:migrate` läuft gegen die Dev-DB fehlerfrei
- Schema wird aus `web/src/server/db/schema/index.ts` exportiert
**Nicht im Scope**
- Auth-Konfiguration, UI

### T004 · Better-Auth-Konfiguration (E-Mail/Passwort, kein Signup)
status: done | depends: T003 | spec: 3.1, 6
`web/src/server/auth.ts` konfiguriert Better Auth mit Drizzle-Adapter (provider "pg"),
E-Mail+Passwort aktiv, öffentliche Registrierung deaktiviert, Rate-Limit aktiv, die
Zusatzfelder aus T003 als `additionalFields`. API-Route `app/api/auth/[...all]/route.ts`.
Helper `getCurrentUser()` und `requireUser()`/`requireAdmin()` in
`web/src/server/session.ts`.
**Akzeptanz**
- Öffentlicher Sign-up-Aufruf wird abgelehnt
- `requireAdmin()` wirft bzw. leitet um, wenn `role !== "admin"`
- Rechte-Helper haben Unit-Tests (Session gemockt)
- `BETTER_AUTH_SECRET` und `BETTER_AUTH_URL` stehen in `web/.env.example`
**Nicht im Scope**
- Login-UI, Einladungen

### T005 · Admin-Seed-Skript
status: done | depends: T004 | spec: 3.9
`npm run seed:admin -- --email a@b.de --password ... --name "Max"` legt einen aktiven
Admin an (über die Better-Auth-Server-API, damit das Passwort korrekt gehasht wird).
Existiert die E-Mail bereits, wird nur `role` auf admin gesetzt.
**Akzeptanz**
- Skript unter `web/scripts/seed-admin.ts`, Aufruf per `tsx`, klare Fehlermeldungen
- Argument-Parsing ist als reine Funktion getestet
**Nicht im Scope**
- UI

### T006 · Login/Logout-UI und Zugriffsschutz
status: open | depends: T004 | spec: 3.1, 6, 7
Mobile-first Login-Seite `/login` (E-Mail, Passwort, deutsche Fehlermeldungen, große
Touch-Ziele), Logout-Button im Layout. Alle Seiten außer `/login`, `/invite/*`,
`/reset-password/*` und `/api/*` erfordern Login (serverseitige Prüfung im Layout bzw.
`proxy.ts`). `robots.txt` verbietet alles, Layout setzt `noindex`.
**Akzeptanz**
- Nicht eingeloggte Aufrufe von `/` landen auf `/login`
- Nach Login Weiterleitung auf `/`; Logout beendet die Session
- `robots.txt` + `noindex`-Meta vorhanden
**Nicht im Scope**
- Einladung, Passwort-Reset, Startseiten-Inhalte

### T007 · Domain: Elo Einzel
status: open | depends: T001 | spec: 3.5
Reine Funktionen in `web/src/domain/elo.ts`: `expectedScore(rA, rB)`,
`kFactor(ratedMatchesInCategory)` (K=40 für die ersten 10, danach 20),
`singlesRatingChange({ ratingA, ratingB, matchesA, matchesB, winner })` → neue Ratings
(gerundet auf ganze Zahlen). Startwert 1000 als Konstante.
**Akzeptanz**
- Tests: gleiche Ratings → ±20 bei K=40; K-Wechsel nach 10 Matches; Summe der
  Änderungen bei gleichem K = 0; Außenseitersieg bringt mehr Punkte
**Nicht im Scope**
- DB, Doppel

### T008 · Domain: Elo Doppel (Team-Mittelwert)
status: open | depends: T007 | spec: 3.5
`doublesRatingChange(teamA, teamB, winner)`: Team-Rating = Mittelwert, erwartete
Gewinnwahrscheinlichkeit aus Team-Ratings, identische Änderung für beide Team-Mitglieder.
K-Faktor pro Spieler aus seiner Doppel-Matchanzahl (dokumentierte Entscheidung: jeder
Spieler nutzt seinen eigenen K).
**Akzeptanz**
- Tests: beide Partner erhalten bei gleichem K dieselbe Änderung; Mittelwertbildung korrekt
**Nicht im Scope**
- DB

### T009 · Domain: Satz- und Ergebnisregeln
status: open | depends: T001 | spec: 3.2
`web/src/domain/score.ts`: `validateSet(a, b)` (bis 21, ab 20:20 zwei Punkte Vorsprung,
Cap 30:29), `validateMatchSets(sets)` (1–3 Sätze, Best-of-3, kein Satz nach Entscheidung),
`determineWinner(sets)`. Rückgabe mit deutschen Fehlermeldungen für die UI.
**Akzeptanz**
- Tests für 21:19, 22:20, 30:29, ungültig 21:20, 31:29, 3. Satz bei 2:0
**Nicht im Scope**
- UI

### T010 · Domain: Match-Status-Workflow
status: open | depends: T001 | spec: 3.3, 3.9
Reine Zustandsmaschine `web/src/domain/match-workflow.ts`: Status draft |
pending_confirmation | published; Aktionen edit, requestPublish, confirm, reject,
adminOverrideConfirm, adminReopen. Funktion `canPerform(action, match, actor)` und
`transition(...)`. Regeln: Bearbeiten nur Beteiligte/Admin und nur in draft; Bestätigen
nur durch die ANDERE Seite als die anfragende; Admin-Override und Reopen nur Admin.
**Akzeptanz**
- Tests decken jede Regel ab, inkl. Selbstbestätigung verboten, Doppel: ein Gegner reicht
**Nicht im Scope**
- DB, Rating

### T011 · Schema-Task: Matches, Teilnehmer, Sätze, Videos
status: open | depends: T003 | spec: 5
Tabellen `matches`, `match_participants`, `match_sets`, `match_videos` gemäß Spec §5
(FKs auf `user`, Enums für match_type/status/team, `onDelete` sinnvoll, Indizes auf
match_id und player_id). Migration generieren und anwenden.
**Akzeptanz**
- Migration läuft fehlerfrei; Enums entsprechen Spec
**Nicht im Scope**
- Services, UI

### T012 · Schema-Task: Rating-Historie, Saisons, Audit-Log, Einladungen
status: open | depends: T011 | spec: 3.1, 3.10, 5
Tabellen `rating_history`, `seasons`, `audit_log` gemäß Spec §5 sowie `invitations`
(id, email, token_hash, created_by, expires_at, accepted_at). Migration.
**Akzeptanz**
- Migration läuft fehlerfrei; Token wird nur gehasht gespeichert
**Nicht im Scope**
- Services, UI

### T013 · Audit-Log-Service
status: open | depends: T012 | spec: 3.10
`web/src/server/services/audit.ts`: `writeAudit(tx, { actorId, action, targetType,
targetId, details })`, nutzbar innerhalb von Transaktionen. Erlaubte `action`-Werte als
Union-Typ (Spec §5 Beispiele).
**Akzeptanz**
- Typisierte Aktionen; Unit-Test für das Mapping der Eingaben
**Nicht im Scope**
- Admin-Ansicht

### T014 · Einladungsflow
status: open | depends: T006, T012, T013 | spec: 3.1, 3.9
Admin-Seite `/admin/invites`: Einladung für E-Mail erzeugen, Link anzeigen (kopierbar,
kein Mailversand nötig), Ablauf 7 Tage. `/invite/[token]`: Anzeigename + Passwort setzen,
legt Spieler an und loggt ein. Abgelaufene/benutzte Tokens werden abgelehnt.
**Akzeptanz**
- Token-Prüfung (Ablauf, einmalig) als reine Funktion getestet
- Nur Admins erreichen `/admin/*` (serverseitig)
- Audit-Eintrag beim Erstellen und Annehmen
**Nicht im Scope**
- E-Mail-Versand

### T015 · Quick-Add: Server-Logik
status: open | depends: T009, T011, T013 | spec: 3.2
Server Action `createDraftMatch(input)` mit Zod-Validierung: Modus, Teams (1 bzw. 2
Spieler pro Team, keine Doppelungen, eingeloggter Nutzer muss beteiligt sein), mindestens
ein Satz (Regeln aus T009). Speichert Match als draft in einer Transaktion, `played_at` =
jetzt, schreibt Audit-Eintrag. Zusätzlich `searchPlayers(query)` für Autocomplete
(nur aktive Spieler, zuletzt gemeinsam gespielte zuerst).
**Akzeptanz**
- Validierung als reine Funktion getestet (Teams, Duplikate, Beteiligung)
**Nicht im Scope**
- UI

### T016 · Quick-Add: Mobile UI
status: open | depends: T015 | spec: 3.2, 7
Großer Button „Neues Match“ auf `/`. Seite `/matches/new`: Umschalter Einzel/Doppel
(Default: zuletzt genutzt), Spielersuche mit Vorschlägen, Satz-Stepper (+/−) statt
Freitext, Speichern legt sofort den Draft an und zeigt ihn. Keine weiteren Pflichtfelder.
**Akzeptanz**
- Touch-Ziele ≥ 44 px; funktioniert bei 375 px Breite
- Fehlermeldungen aus der Validierung werden deutsch angezeigt
**Nicht im Scope**
- Offline-Queue (T028)

### T017 · Draft ansehen und bearbeiten
status: open | depends: T010, T016 | spec: 3.3
Seite `/matches/[id]` mit Status-Badge (Draft/Wartet auf Bestätigung/Veröffentlicht,
farblich unterscheidbar). Beteiligte und Admins können im Status draft Sätze, Datum, Ort,
Notizen bearbeiten (Rechte über `canPerform`). Audit-Eintrag bei Änderung.
**Akzeptanz**
- Unberechtigte Bearbeitung wird serverseitig abgelehnt
**Nicht im Scope**
- Publish-Workflow

### T018 · Publish anfragen, bestätigen, ablehnen
status: open | depends: T017 | spec: 3.3, 7
Server Actions + Buttons: „Bestätigung anfragen“ (→ pending, speichert anfragende Seite),
„Bestätigen“ (nur andere Seite, → published, setzt confirmed_*/published_at), „Ablehnen“
mit optionalem Kommentar (→ draft). Nutzt `transition()` aus T010. Rating wird noch NICHT
berechnet (T019). Alles mit Audit-Log.
**Akzeptanz**
- Statuswechsel transaktional; unerlaubte Übergänge liefern verständliche Fehler
**Nicht im Scope**
- Rating-Berechnung

### T019 · Rating-Update beim Veröffentlichen
status: open | depends: T008, T018 | spec: 3.3, 3.5
Beim Übergang nach published in derselben Transaktion: passende Kategorie berechnen
(T007/T008), `rating_history` je Spieler schreiben (reason "match_published"),
denormalisierte Ratings in `user` aktualisieren. Matchanzahl je Kategorie für den K-Faktor
aus nicht-revertierter Historie.
**Akzeptanz**
- Service-Funktion trennt Berechnung (rein, getestet) von Persistenz
**Nicht im Scope**
- Reopen/Revert

### T020 · Admin: Reopen mit Revert und Bestätigungs-Override
status: open | depends: T019 | spec: 3.3, 3.9, 3.10
Admin kann published Matches reopenen: Match → draft, zugehörige `rating_history`
als `reverted` markieren (nicht löschen), Ratings zurücksetzen. Admin-Override bestätigt ein
pending Match im Namen der Gegenseite. Beides mit Audit-Log.
**Akzeptanz**
- Revert-Berechnung als reine Funktion getestet
**Nicht im Scope**
- Nachträgliche Neuberechnung späterer Matches (dokumentierte Vereinfachung)

### T021 · In-App-Hinweis „Wartet auf deine Bestätigung“
status: open | depends: T018 | spec: 3.3, 7, 8
Startseite zeigt oben eine Liste pending Matches, die der eingeloggte Nutzer bestätigen
darf, mit Ein-Tap-Buttons Bestätigen/Ablehnen.
**Akzeptanz**
- Nur für berechtigte Nutzer sichtbar; Abfrage serverseitig
**Nicht im Scope**
- Push/E-Mail (siehe T090)

### T022 · Video-Links pro Match
status: open | depends: T017 | spec: 3.4
Liste von Video-URLs mit optionalem Label pro Match, auch nachträglich bei published
Matches (ohne Rating-Neuberechnung). YouTube-URLs → Embed (youtube-nocookie), sonst
einfacher externer Link.
**Akzeptanz**
- URL-Erkennung als reine Funktion getestet (youtube.com, youtu.be, Sonstiges)
**Nicht im Scope**
- Upload/Hosting

### T023 · Ligatabellen Einzel und Doppel
status: open | depends: T019 | spec: 3.6
Seite `/standings` mit Tabs Einzel/Doppel: Platz, Name, Rating, Matches, S/N, Siegquote,
Trend (Summe der letzten 5 Änderungen, Pfeil). Nur aktive Spieler, nur published Matches.
**Akzeptanz**
- Tabellen-Aufbereitung als reine Funktion getestet; mobil lesbar
**Nicht im Scope**
- Saisonfilter (T026)

### T024 · Spielerprofil
status: open | depends: T023 | spec: 3.1, 3.7
`/players/[id]`: beide Ratings, Rating-Verlauf je Kategorie (einfache SVG-Linie, keine
schwere Chart-Lib nötig), Bilanz je Kategorie, Match-Historie mit Filter Einzel/Doppel.
Eigenes Profil: Anzeigename ändern.
**Akzeptanz**
- Aufbereitung der Verlaufsdaten getestet
**Nicht im Scope**
- Profilfoto-Upload

### T025 · Head-to-Head und Paarungs-Historie
status: open | depends: T024 | spec: 3.7
Einzel: Bilanz, Satzverhältnis, letzte Begegnungen zweier Spieler. Doppel: Duo-gegen-Duo-
Historie.
**Akzeptanz**
- Aggregation als reine Funktion getestet
**Nicht im Scope**
- Partner-Statistik (T092)

### T026 · Saisons
status: open | depends: T023 | spec: 3.8, 3.9
Admin legt Saisons an (Name, Start, Ende). Ligatabelle filterbar nach Saison
(Statistiken im Zeitraum; Rating läuft durchgängig weiter, kein Reset – siehe offene Frage).
**Akzeptanz**
- Zeitraumfilter getestet; nur Admin darf Saisons anlegen
**Nicht im Scope**
- Rating-Reset pro Saison

### T027 · Admin: Nutzerverwaltung, Rating-Korrektur, Audit-Ansicht
status: open | depends: T020, T014 | spec: 3.9, 3.10
Nutzer deaktivieren/reaktivieren (kein Löschen), manuelle Rating-Korrektur mit
Pflicht-Begründung (rating_history ohne match_id), Audit-Log-Liste (nur Admin, neueste
zuerst, paginiert).
**Akzeptanz**
- Begründung ist serverseitig Pflicht; alles im Audit-Log
**Nicht im Scope**
- Rollenwechsel per UI

### T028 · Passwort-Reset per E-Mail
status: open | depends: T006 | spec: 3.1
Better-Auth-Reset-Flow. Mailversand über eine kleine Mailer-Abstraktion mit SMTP
(Dev: Mailpit aus `compose.dev.yml`, Port 1025). Seiten „Passwort vergessen“ und
`/reset-password/[token]`.
**Akzeptanz**
- SMTP-Konfiguration über Env-Variablen; ohne SMTP wird der Link geloggt statt zu crashen
**Nicht im Scope**
- Andere Benachrichtigungen

### T029 · PWA
status: open | depends: T016 | spec: 4, 7
Web-App-Manifest (Name, Icons als generierte SVG/PNG, Theme-Farbe), Shortcut
„Neues Match“ → `/matches/new`, Installierbarkeit auf iOS/Android.
**Akzeptanz**
- Manifest valide; Shortcut vorhanden
**Nicht im Scope**
- Offline-Caching der Daten

### T030 · Quick-Add bei schlechter Verbindung
status: open | depends: T029 | spec: 6
Optimistisches UI beim Speichern, verständliche Fehlermeldung, erneuter Versuch ohne
Datenverlust (Formularzustand bleibt erhalten; optional lokaler Entwurf im Browser).
**Akzeptanz**
- Doppeltes Absenden erzeugt kein doppeltes Match (Idempotenz-Key)
**Nicht im Scope**
- Vollständige Offline-Synchronisation

### T031 · Produktions-Deployment mit Docker Compose
status: open | depends: T006 | spec: 4
`web/Dockerfile` (Next.js standalone, Multi-Stage), `compose.yml` (App + Postgres +
Volume), Migrationen beim Start, App bindet an 0.0.0.0, Anleitung für Tailscale in README
des `web/`-Ordners.
**Akzeptanz**
- `docker compose -f compose.yml build` läuft
**Nicht im Scope**
- Öffentliche Erreichbarkeit, Reverse-Proxy

### T032 · Automatisches DB-Backup
status: open | depends: T031 | spec: 6
Backup-Service in `compose.yml` (täglicher `pg_dump`, Aufbewahrung per Env, z. B. 14 Tage).
**Akzeptanz**
- Aufbewahrungslogik dokumentiert und konfigurierbar
**Nicht im Scope**
- Offsite-Backup

## Blocked / Rückfragen an den Menschen

### T090 · Push-/E-Mail-Benachrichtigungen
status: blocked | depends: T021 | spec: 11
> BLOCKED: Offene Frage 11 – reicht der In-App-Hinweis (T021) oder werden Push/E-Mail gewünscht?

### T091 · Zuschauer-/Read-only-Rolle
status: blocked | depends: T023 | spec: 2, 11
> BLOCKED: Offene Frage 11 – Zuschauerrolle gewünscht? Mit oder ohne Login?

### T092 · Partner-Statistik im Doppel
status: blocked | depends: T025 | spec: 11
> BLOCKED: Offene Frage 11 – Statistik „erfolgreichster Partner“ gewünscht?
