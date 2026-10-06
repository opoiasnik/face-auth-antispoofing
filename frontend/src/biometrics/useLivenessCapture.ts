import { useCallback, useEffect, useRef, useState, type RefObject } from "react";

import { biometricsApi, type CaptureBody } from "@/api/endpoints";
import type { ChallengeAction, ChallengePurpose, Frame } from "@/api/types";
import { captureFrame } from "@/camera/frames";

import { captureOffsets, sleep } from "./schedule";

export type CapturePhase = "idle" | "challenge" | "capturing" | "verifying";

export interface CaptureProgress {
  phase: CapturePhase;
  actions: ChallengeAction[];
  step: number;
  /** 0..1 progress within the current step */
  stepProgress: number;
}

const IDLE: CaptureProgress = { phase: "idle", actions: [], step: 0, stepProgress: 0 };

/**
 * Runs a liveness session: obtains a challenge, guides the user through the
 * random head movements while capturing frames, then hands the frames to
 * ``submit`` (enrollment / verification / identification).
 */
export function useLivenessCapture(videoRef: RefObject<HTMLVideoElement | null>) {
  const [progress, setProgress] = useState<CaptureProgress>(IDLE);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const run = useCallback(
    async <T>(purpose: ChallengePurpose, submit: (body: CaptureBody) => Promise<T>): Promise<T> => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      const { signal } = controller;

      try {
        setProgress({ ...IDLE, phase: "challenge" });
        const challenge = await biometricsApi.createChallenge(purpose, signal);
        const { step_duration_ms: stepDuration } = challenge.capture;
        const offsets = captureOffsets(challenge.capture);
        const frames: Frame[] = [];

        for (let step = 0; step < challenge.actions.length; step++) {
          const stepStart = performance.now();
          setProgress({ phase: "capturing", actions: challenge.actions, step, stepProgress: 0 });
          for (const offset of offsets) {
            await sleep(Math.max(0, offset - (performance.now() - stepStart)), signal);
            const video = videoRef.current;
            if (!video) throw new Error("Kamera nie je dostupná");
            frames.push({ step, image: captureFrame(video) });
            setProgress((p) => ({ ...p, stepProgress: offset / stepDuration }));
          }
          await sleep(Math.max(0, stepDuration - (performance.now() - stepStart)), signal);
        }

        setProgress((p) => ({ ...p, phase: "verifying", stepProgress: 1 }));
        return await submit({ challenge_id: challenge.challenge_id, frames });
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
        setProgress(IDLE);
      }
    },
    [videoRef],
  );

  const cancel = useCallback(() => abortRef.current?.abort(), []);

  return { progress, run, cancel };
}
