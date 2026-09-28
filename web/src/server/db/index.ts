import { drizzle } from "drizzle-orm/node-postgres";
import pg from "pg";

import * as schema from "./schema";

// Ein Pool pro Prozess (auch bei Hot-Reload in der Entwicklung).
const globalForDb = globalThis as unknown as { pgPool?: pg.Pool };

export const pool =
  globalForDb.pgPool ??
  new pg.Pool({ connectionString: process.env.DATABASE_URL });
if (process.env.NODE_ENV !== "production") globalForDb.pgPool = pool;

// Drizzle-Client mit expliziter `client`-Option aufsetzen.
export const db = drizzle({ client: pool, schema });
export type Db = typeof db;
