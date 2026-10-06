import { describe, expect, it } from "vitest";

import { ApiError } from "@/api/http";

import { describeError, qualityHints } from "./messages";

describe("describeError", () => {
  it("prefers the biometric rejection reason", () => {
    const error = new ApiError(401, "biometric_rejected", "x", { reason: "passive_spoof" });
    expect(describeError(error)).toMatch(/podvrh/);
  });

  it("falls back to the error code and then to the message", () => {
    expect(describeError(new ApiError(429, "too_many_requests", "x"))).toMatch(/Príliš veľa/);
    expect(describeError(new ApiError(500, "weird", "raw message"))).toBe("raw message");
  });
});

describe("qualityHints", () => {
  it("orders hints by frequency", () => {
    const error = new ApiError(401, "biometric_rejected", "x", {
      quality_issues: { too_dark: 1, no_face: 4 },
    });
    expect(qualityHints(error)).toEqual([
      "Tvár nie je v zábere",
      "Príliš tma – zlepšite osvetlenie tváre",
    ]);
  });
});
