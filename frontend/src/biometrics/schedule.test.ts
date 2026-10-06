import { describe, expect, it } from "vitest";

import { captureOffsets } from "./schedule";

describe("captureOffsets", () => {
  it("spreads frames after the lead-in", () => {
    const offsets = captureOffsets({ frames_per_step: 5, step_duration_ms: 2200, lead_in_ms: 700 });
    expect(offsets).toEqual([850, 1150, 1450, 1750, 2050]);
  });

  it("never schedules before the lead-in or after the step", () => {
    const offsets = captureOffsets({ frames_per_step: 3, step_duration_ms: 1000, lead_in_ms: 400 });
    expect(Math.min(...offsets)).toBeGreaterThanOrEqual(400);
    expect(Math.max(...offsets)).toBeLessThan(1000);
  });
});
