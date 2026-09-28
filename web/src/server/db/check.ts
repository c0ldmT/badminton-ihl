import type { NodePgDatabase } from "drizzle-orm/node-postgres";
import { sql } from "drizzle-orm";

/**
 * Prüft die Datenbankverbindung, indem `"select 1"` ausgeführt wird.
 * Gibt `"up"` bei Erfolg und `"down"` zurück – niemals eine Exception.
 */
export async function verifyDbConnection(
  db: NodePgDatabase<Record<string, unknown>>,
): Promise<"up" | "down"> {
  try {
    // `db.execute()` ist die Raw-SQL-API; der Rückgabewert wird per Cast zum
    // awaited Promise gemacht (typisiert als PgRaw in Drizzle).
    await (db.execute(sql`select 1`) as unknown as Promise<unknown>);
    return "up";
  } catch {
    return "down";
  }
}
