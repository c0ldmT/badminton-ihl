// Drizzle-Schema für die von Better Auth verwalteten Tabellen (user, session,
// account, verification) – nach der Spec §5 + Better-Auth-Konventionen.
// Die `users`-Tabelle ist zugleich die Spieler-Tabelle der Liga und enthält
// die in Spec §5 / TASKS.md T003 beschriebenen Zusatzfelder.

import { pgTable, text, boolean, integer, timestamp } from "drizzle-orm/pg-core";

//------------------------------------------------------------------------------
// 1. users  (= players / BetterAuth-Benutzertabelle)
//------------------------------------------------------------------------------
export const users = pgTable("users", {
  // Kernfelder von Better Auth (coreSchema + userSchema)
  id: text("id").primaryKey(),
  email: text("email").notNull().unique(),
  emailVerified: boolean("email_verified").notNull().default(false),
  name: text("name"),
  image: text("image"),

  // Zusatzfelder aus Spec §5 / T003
  displayName: text("display_name").notNull(),
  isActive: boolean("is_active").notNull().default(true),
  role: text("role", { enum: ["player", "admin"] }).notNull().default("player"),
  ratingSingles: integer("rating_singles").notNull().default(1000),
  ratingDoubles: integer("rating_doubles").notNull().default(1000),

  // Zeitstempel von coreSchema
  createdAt: timestamp("created_at", { mode: "string" }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { mode: "string" }).defaultNow().notNull(),
});

//------------------------------------------------------------------------------
// 2. sessions
//------------------------------------------------------------------------------
export const sessions = pgTable("sessions", {
  id: text("id").primaryKey(),
  userId: text("user_id").notNull(),
  expiresAt: timestamp("expires_at"),
  token: text("token").notNull().unique(),
  ipAddress: text("ip_address"),
  userAgent: text("user_agent"),

  createdAt: timestamp("created_at", { mode: "string" }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { mode: "string" }).defaultNow().notNull(),
});

//------------------------------------------------------------------------------
// 3. accounts
//------------------------------------------------------------------------------
export const accounts = pgTable("accounts", {
  id: text("id").primaryKey(),
  userId: text("user_id").notNull(),
  providerId: text("provider_id").notNull(),
  accountId: text("account_id").notNull(),
  accessToken: text("access_token"),
  refreshToken: text("refresh_token"),
  idToken: text("id_token"),
  accessTokenExpiresAt: timestamp("access_token_expires_at"),
  refreshTokenExpiresAt: timestamp("refresh_token_expires_at"),
  scope: text("scope"),
  password: text("password"),

  createdAt: timestamp("created_at", { mode: "string" }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { mode: "string" }).defaultNow().notNull(),
});

//------------------------------------------------------------------------------
// 4. verifications   (E-Mail-Verification / Password-Reset-Tokens)
//------------------------------------------------------------------------------
export const verifications = pgTable("verifications", {
  id: text("id").primaryKey(),
  userId: text("user_id"),
  value: text("value").notNull().unique(),
  expiresAt: timestamp("expires_at").notNull(),
  identifier: text("identifier").notNull(),

  createdAt: timestamp("created_at", { mode: "string" }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { mode: "string" }).defaultNow().notNull(),
});
