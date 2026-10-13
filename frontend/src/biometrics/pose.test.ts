import { describe, expect, it } from "vitest";

import { medianPose, movementProgress } from "./pose";

const capture = { yaw_threshold: 0.2, pitch_threshold: 0.07 };
const baseline = { yaw: 0.05, pitch: 0.55 };

describe("movementProgress", () => {
  it("measures turns relative to the neutral pose", () => {
    expect(movementProgress("turn_left", { yaw: 0.25, pitch: 0.55 }, baseline, capture)).toBeCloseTo(1);
    expect(movementProgress("turn_right", { yaw: 0.25, pitch: 0.55 }, baseline, capture)).toBeLessThan(0);
  });

  it("uses the pitch threshold for vertical movements", () => {
    expect(movementProgress("look_up", { yaw: 0, pitch: 0.48 }, baseline, capture)).toBeCloseTo(1);
    expect(movementProgress("look_down", { yaw: 0, pitch: 0.62 }, baseline, capture)).toBeCloseTo(1);
  });
});

describe("medianPose", () => {
  it("is robust to a single outlier", () => {
    const pose = medianPose([
      { yaw: 0.01, pitch: 0.5 },
      { yaw: 0.02, pitch: 0.52 },
      { yaw: 0.9, pitch: 0.1 },
    ]);
    expect(pose).toEqual({ yaw: 0.02, pitch: 0.5 });
    expect(medianPose([])).toBeNull();
  });
});
