import { NextResponse } from "next/server";

import { db } from "@/server/db";
import type { NodePgDatabase } from "drizzle-orm/node-postgres";
import { verifyDbConnection } from "@/server/db/check";

export interface HealthResponse {
  status: "ok";
  db: "up" | "down";
}

/**
 * GET /api/health – Gibt den Service-Status inkl. DB-Ping zurück.
 */
export async function GET(): Promise<NextResponse<HealthResponse>> {
  const dbStatus = await verifyDbConnection(db as NodePgDatabase<Record<string, unknown>>);

  const res: HealthResponse = { status: "ok", db: dbStatus };
  const statusCode = dbStatus === "down" ? 503 : 200;

  return new NextResponse(JSON.stringify(res), {
    status: statusCode,
    headers: { "Content-Type": "application/json" },
  });
}
