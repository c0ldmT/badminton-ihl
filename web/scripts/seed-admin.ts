/**
 * seed-admin.ts – CLI zum Anlegen oder Aktivieren eines Admin-Nutzers.
 *
 * Aufruf:
 *   npx tsx scripts/seed-admin.ts --email max@liga.de --password geheim --name "Max Mustermann"
 *
 * - `--email`  (mandatory)  E-Mail-Adresse des Admins
 * - `--password` (mandatory) Passwort für den Admin-Account
 * - `--name`   (optional)   Anzeigename; Standard: E-Mail-Lokalteil
 */

import process from "node:process";

import { drizzle } from "drizzle-orm/node-postgres";
import pg from "pg";

import { eq, sql } from "drizzle-orm";

import * as schema from "@/server/db/schema";
import { hashPassword } from "@better-auth/utils/password";

// ── Types ────────────────────────────────────────────────────────────

export interface SeedConfig {
  email: string;
  password: string;
  name?: string;
}

/** Fehler, wenn die CLI-Argumente ungültig sind. */
export class ParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ParseError";
  }
}

// ── Parsing-Funktion (rein, unit-testbar) ───────────────────────────

/**
 * CLI-Flags parsen.
 *
 * Erwartet die Argumente als String-Array (...("--key" "val") ...).
 * Gibt ein SeedConfig-Objekt zurück.
 * Wirft {@link ParseError}, wenn --email oder --password fehlen
 * oder unbekannte --Flags vorkommen.
 */
export function parseArgs(raw: string[]): SeedConfig {
  let email: string | undefined;
  let password: string | undefined;
  let name: string | undefined;

  for (let i = 0; i < raw.length; i++) {
    switch (raw[i]) {
      case "--email":
        email = raw[++i];
        break;
      case "--password":
        password = raw[++i];
        break;
      case "--name":
        name = raw[++i];
        break;
      default:
        if (raw[i].startsWith("--")) {
          throw new ParseError(
            `Unbekannter Flag «${raw[i]}» — --email, --password und --name sind erlaubt.`,
          );
        }
    }
  }

  if (!email) {
    throw new ParseError("--email ist erforderlich.");
  }

  if (!password) {
    throw new ParseError("--password ist erforderlich.");
  }

  return { email, password, name };
}

// ── Hauptlogik ──────────────────────────────────────────────────────

async function seedAdmin(config: SeedConfig): Promise<void> {
  const DATABASE_URL = process.env.DATABASE_URL;
  if (!DATABASE_URL) {
    throw new Error("$DATABASE_URL nicht gesetzt.");
  }

  const pool = new pg.Pool({ connectionString: DATABASE_URL });
  const db = drizzle(pool, { schema });

  try {
    // Prüfen ob User existiert (Better Auth speichert Passwörter in accounts,
    // existence check also über users.email).
    const raw = await db.execute(
      sql`SELECT * FROM users WHERE email = ${config.email} LIMIT 1`,
    );
    // Cast ist nötig, weil `db.execute()` QueryResult zurückgibt,
    // das die Array-Interface von `$inferSelect[]` nicht direkt hat.
    const existingUsers = raw as unknown as typeof schema.users.$inferSelect[];

    if (existingUsers.length > 0) {
      console.log(`INFO: User '${config.email}' existiert bereits → Rolle wird aktualisiert.`);
      return updateRoleToAdmin(config.name ?? config.email, config.email, db);
    }

    // Neuer User – Passwort hashen und anlegen.
    const passwordHash = await hashPassword(config.password);

    const created: typeof schema.users.$inferSelect[] = [];

    // 1) User row erstellen.
    const newId = crypto.randomUUID();
    await db
      .insert(schema.users)
      .values({
        id: newId,
        email: config.email,
        name: config.name,
        displayName: config.name ?? config.email.split("@")[0],
        isActive: true,
        role: "admin",
        ratingSingles: 1000,
        ratingDoubles: 1000,
      })
      .returning()
      .then((rows) => created.push(...rows));

    // 2) Account row erstellen (Better Auth erwartet credentials in accounts).
    await db.insert(schema.accounts).values({
      id: crypto.randomUUID(),
      userId: newId,
      providerId: "credential",
      accountId: config.email,
      password: String(passwordHash),
    });

    process.stdout.write(
      `ERFOG: Admin '${created[0]?.name ?? config.email}' (${config.email}) angelegt.\n`,
    );
  } finally {
    await pool.end();
  }
}

/**
 * Vorhandener Benutzer auf admin aufwerten.
 */
async function updateRoleToAdmin(
  displayName: string,
  email: string,
  db: ReturnType<typeof drizzle>,
): Promise<void> {
  const updated = await db
    .update(schema.users)
    .set({ role: "admin", displayName })
    .where(eq(schema.users.email, email))
    .returning();

  if (updated.length > 0) {
    process.stdout.write(
      `ERFOLG: Rolle für ${email} auf 'admin' gesetzt.\n`,
    );
  } else {
    process.stdout.write(`INFO: ${email} ist bereits Admin.\n`);
  }
}

// ── Ausführung bei direktem Aufruf ─────────────────────────────────

async function main(): Promise<void> {
  const rawArgs = process.argv.slice(2);

  // --help behandeln.
  if (rawArgs.includes("--help") || rawArgs.includes("-h")) {
    process.stdout.write(
      `Usage: npm run seed:admin -- --email EMAIL --password PASSWORD [--name NAME]
  --email      E-Mail-Adresse des Admins   (erforderlich)
  --password   Passwort                   (erforderlich)
  --name       Anzeigename                (optional, Standard: E-Mail-Lokalteil)\n`,
    );
    process.exit(0);
  }

  let config: SeedConfig;
  try {
    config = parseArgs(rawArgs);
  } catch (err) {
    const msg = err instanceof ParseError ? err.message : String(err);
    process.stdout.write(`FEHLER: ${msg}\n`);
    process.exit(1);
  }

  if (!config.email && !config.password) {
    // parseArgs hat kein Error geworfen → leer aufgerufen → Hilfe anzeigen.
    process.stdout.write("HINWEIS: --email und --password werden benötigt.\n");
    process.exit(0);
  }

  try {
    await seedAdmin(config);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    process.stdout.write(`FEHLER: ${msg}\n`);
    process.exit(1);
  }
}

// Nur ausführen, wenn dieses Skript direkt aufgerufen wird
// (nicht über `import`; damit funktioniert das Modul auch in Tests).
if (process.argv[1] && import.meta.url.replace(/\\/g, "/").endsWith(process.argv[1].replace(/\\/g, "/"))) {
  main();
}
