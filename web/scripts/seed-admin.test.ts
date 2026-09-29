/**
 * seed-admin.test.ts – Unit-Tests für die parseArgs-Funktion.
 */

import { describe, it, expect } from "vitest";
import { parseArgs, ParseError } from "./seed-admin";

describe("parseArgs", () => {
  // ── Valid input ─────────────────────────────────────────────────────

  it("parsiert --email und --password korrekt", () => {
    const result = parseArgs(["--email", "max@liga.de", "--password", "geheim"]);
    expect(result).toEqual({ email: "max@liga.de", password: "geheim" });
  });

  it("parsiert auch optionalen --name mit", () => {
    const result = parseArgs([
      "--email", "max@liga.de",
      "--password", "geheim",
      "--name", "Max Mustermann",
    ]);
    expect(result).toEqual({
      email: "max@liga.de",
      password: "geheim",
      name: "Max Mustermann",
    });
  });

  it("erlaubt andere Flag-Reihenfolge", () => {
    const result = parseArgs([
      "--password", "geheim",
      "--email", "max@liga.de",
    ]);
    expect(result).toEqual({ email: "max@liga.de", password: "geheim" });
  });

  it("erlaubt beliebige Reihenfolge (name→password→email)", () => {
    const result = parseArgs([
      "--name", "Max Mustermann",
      "--password", "geheim",
      "--email", "max@liga.de",
    ]);
    expect(result).toEqual({
      email: "max@liga.de",
      password: "geheim",
      name: "Max Mustermann",
    });
  });

  // ── Edge cases ──────────────────────────────────────────────────────

  it("nimmt leeren --name-Wert als leere String auf", () => {
    const result = parseArgs([
      "--email", "max@liga.de",
      "--password", "geheim",
      "--name", "",
    ]);
    expect(result.name).toBe("");
  });

  it("ignoriert nicht '--' beginnende Flags (z.B. positional)", () => {
    const result = parseArgs([
      "--email", "a@b.de",
      "positional",
      "--password", "x",
    ]);
    expect(result.email).toBe("a@b.de");
    expect(result.password).toBe("x");
  });

  // ── Fehlende / ungültige Flags ─────────────────────────────────────

  it("wirft ParseError bei fehlendem --email", () => {
    expect(() => parseArgs(["--password", "x"])).toThrow(ParseError);
  });

  it("wirft ParseError bei fehlendem --password", () => {
    expect(() => parseArgs(["--email", "a@b.de"])).toThrow(ParseError);
  });

  it("wirft ParseError bei komplett leerem Array", () => {
    expect(() => parseArgs([])).toThrow(ParseError);
  });

  it("wirft ParseError bei unbekannten Flags ('--foo')", () => {
    expect(() =>
      parseArgs(["--email", "a@b.de", "--password", "x", "--unbekannt"]),
    ).toThrow(/^Unbekannter Flag/);
  });

  it("wirft ParseError bei mehrfachen unbekannten Flags", () => {
    expect(() =>
      parseArgs(["--foo", "--bar"]),
    ).toThrow(/^Unbekannter Flag/);
  });

  // ── Sonderfälle ─────────────────────────────────────────────────────

  it("parsiert Passwort mit Sonderzeichen", () => {
    const result = parseArgs([
      "--email", "mario@liga.de",
      "--password", "p@$$w0rd!#%",
    ]);
    expect(result.password).toBe("p@$$w0rd!#%");
  });

  it("parsiert E-Mail mit Subdomain und Unterstrich", () => {
    const result = parseArgs([
      "--email", "max.mustermann@mail.badminton-ihl.de",
      "--password", "secure123!",
    ]);
    expect(result.email).toBe("max.mustermann@mail.badminton-ihl.de");
  });

  it("parsiert --name mit Leerschritten korrekt", () => {
    const result = parseArgs([
      "--email", "a@b.de",
      "--password", "x",
      "--name", "Muhammad Ali Jones III",
    ]);
    expect(result.name).toBe("Muhammad Ali Jones III");
  });

  it("liefert Name als undefined wenn nicht angegeben", () => {
    const result = parseArgs(["--email", "a@b.de", "--password", "x"]);
    expect(result.name).toBeUndefined();
  });
});
