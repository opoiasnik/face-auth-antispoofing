import { useCallback, useEffect, useRef, useState, type RefObject } from "react";

import { biometricsApi, type CaptureBody } from "@/api/endpoints";
import type { Challenge, ChallengeAction, ChallengePurpose, Frame } from "@/api/types";
import { captureFrame } from "@/camera/frames";
import { QUALITY_MAX_WIDTH } from "@/config";

import { medianPose, movementProgress, type Pose } from "./pose";
import { pickShots, type Shot } from "./sampling";
import { sleep } from "./schedule";

export type CapturePhase = "idle" | "challenge" | "capturing" | "verifying";

export interface CaptureProgress {
  phase: CapturePhase;
  actions: ChallengeAction[];
  step: number;
  stepProgress: number;
  stepDone: boolean;
}

const IDLE: CaptureProgress = { phase: "idle", actions: [], step: 0, stepProgress: 0, stepDone: false };
const STEP_PAUSE_MS = 300;
const LOOK_BACK_INTERVALS = 2;

const clamp01 = (value: number) => Math.min(1, Math.max(0, value));

export function useLivenessCapture(videoRef: RefObject<HTMLVideoElement | null>) {
  const [progress, setProgress] = useState<CaptureProgress>(IDLE);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const grab = useCallback(
    (maxWidth?: number, quality?: number) => {
      const video = videoRef.current;
      if (!video) throw new Error("Kamera nie je dostupná");
      return captureFrame(video, maxWidth, quality);
    },
    [videoRef],
  );

  const captureStep = useCallback(
    async (
      challenge: Challenge,
      step: number,
      baseline: Pose | null,
      centerPoses: Pose[],
      signal: AbortSignal,
    ): Promise<Frame[]> => {
      const cap = challenge.capture;
      const action = challenge.actions[step]!;
      const isCenter = action === "center";
      const shots: Shot<Frame>[] = [];
      const start = performance.now();
      let detectedAt: number | null = null;
      let pending = false;

      const readPose = () => {
        if (pending) return;
        pending = true;
        const sentAt = performance.now();
        biometricsApi
          .checkQuality(grab(QUALITY_MAX_WIDTH, 0.7), signal)
          .then((result) => {
            if (result.yaw === null || result.pitch === null) return;
            const pose = { yaw: result.yaw, pitch: result.pitch };
            if (isCenter) {
              centerPoses.push(pose);
              return;
            }
            if (!baseline) return;
            const moved = movementProgress(action, pose, baseline, cap);
            setProgress((p) => ({ ...p, stepProgress: Math.max(p.stepProgress, clamp01(moved)) }));
            if (moved >= 1 && detectedAt === null) {
              detectedAt = sentAt;
              setProgress((p) => ({ ...p, stepDone: true }));
            }
          })
          .catch(() => undefined)
          .finally(() => {
            pending = false;
          });
      };

      for (;;) {
        const now = performance.now();
        const elapsed = now - start;
        if (isCenter) {
          if (elapsed >= cap.center_duration_ms) break;
          setProgress((p) => ({ ...p, stepProgress: elapsed / cap.center_duration_ms }));
        } else {
          if (detectedAt !== null && now - detectedAt >= cap.hold_after_detection_ms) break;
          if (elapsed >= cap.action_timeout_ms) break;
          if (!baseline) setProgress((p) => ({ ...p, stepProgress: elapsed / cap.action_timeout_ms }));
        }
        shots.push({ item: { step, image: grab() }, at: performance.now() });
        readPose();
        await sleep(cap.frame_interval_ms, signal);
      }
      return pickShots(shots, detectedAt, cap.max_frames_per_step, cap.frame_interval_ms * LOOK_BACK_INTERVALS);
    },
    [grab],
  );

  const run = useCallback(
    async <T>(purpose: ChallengePurpose, submit: (body: CaptureBody) => Promise<T>): Promise<T> => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      const { signal } = controller;

      try {
        setProgress({ ...IDLE, phase: "challenge" });
        const challenge = await biometricsApi.createChallenge(purpose, signal);
        const frames: Frame[] = [];
        const centerPoses: Pose[] = [];
        let baseline: Pose | null = null;

        for (let step = 0; step < challenge.actions.length; step++) {
          setProgress({
            phase: "capturing",
            actions: challenge.actions,
            step,
            stepProgress: 0,
            stepDone: false,
          });
          frames.push(...(await captureStep(challenge, step, baseline, centerPoses, signal)));
          if (step === 0) baseline = medianPose(centerPoses);
          setProgress((p) => ({ ...p, stepProgress: 1, stepDone: true }));
          await sleep(STEP_PAUSE_MS, signal);
        }

        setProgress((p) => ({ ...p, phase: "verifying" }));
        return await submit({ challenge_id: challenge.challenge_id, frames });
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
        setProgress(IDLE);
      }
    },
    [captureStep],
  );

  const cancel = useCallback(() => abortRef.current?.abort(), []);

  return { progress, run, cancel };
}
