import { describe, it, expect, vi } from "vitest";

import { verifyDbConnection } from "./check";

describe("verifyDbConnection", () => {
  it("gibt 'up' zurück wenn die Verbindung funktioniert", async () => {
    const executeSpy = vi.fn().mockResolvedValue([]);
    const mockDb = { execute: executeSpy };
    const result = await verifyDbConnection(mockDb as never);

    expect(result).toBe("up");
    expect(executeSpy).toHaveBeenCalledTimes(1);
  });

  it("gibt 'down' zurück bei einem Fehler", async () => {
    const executeSpy = vi.fn().mockRejectedValue(new Error("simulated connection error"));
    const mockDb = { execute: executeSpy };
    const result = await verifyDbConnection(mockDb as never);

    expect(result).toBe("down");
    expect(executeSpy).toHaveBeenCalledTimes(1);
  });
});
