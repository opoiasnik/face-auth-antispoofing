import type { CaptureParameters, ChallengeAction } from "@/api/types";

export interface Pose {
  yaw: number;
  pitch: number;
}

export function medianPose(poses: Pose[]): Pose | null {
  if (poses.length === 0) return null;
  const median = (values: number[]) => {
    const sorted = [...values].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[mid]! : (sorted[mid - 1]! + sorted[mid]!) / 2;
  };
  return { yaw: median(poses.map((p) => p.yaw)), pitch: median(poses.map((p) => p.pitch)) };
}

export function movementProgress(
  action: ChallengeAction,
  pose: Pose,
  baseline: Pose,
  capture: Pick<CaptureParameters, "yaw_threshold" | "pitch_threshold">,
): number {
  switch (action) {
    case "turn_left":
      return (pose.yaw - baseline.yaw) / capture.yaw_threshold;
    case "turn_right":
      return (baseline.yaw - pose.yaw) / capture.yaw_threshold;
    case "look_up":
      return (baseline.pitch - pose.pitch) / capture.pitch_threshold;
    case "look_down":
      return (pose.pitch - baseline.pitch) / capture.pitch_threshold;
    default:
      return 0;
  }
}
