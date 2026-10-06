import { useEffect, useState, type RefObject } from "react";

import { biometricsApi } from "@/api/endpoints";
import type { QualityCheck } from "@/api/types";
import { captureFrame } from "@/camera/frames";
import { QUALITY_MAX_WIDTH, QUALITY_POLL_MS } from "@/config";

import { sleep } from "./schedule";

/** Periodically asks the server whether the face is well positioned (pre-flight guidance). */
export function useQualityMonitor(
  videoRef: RefObject<HTMLVideoElement | null>,
  enabled: boolean,
): QualityCheck | null {
  const [quality, setQuality] = useState<QualityCheck | null>(null);

  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    const poll = async () => {
      while (!controller.signal.aborted) {
        const video = videoRef.current;
        if (video?.videoWidth) {
          try {
            const image = captureFrame(video, QUALITY_MAX_WIDTH, 0.8);
            setQuality(await biometricsApi.checkQuality(image, controller.signal));
          } catch {
            // transient errors are ignored, the next poll retries
          }
        }
        await sleep(QUALITY_POLL_MS, controller.signal).catch(() => undefined);
      }
    };
    void poll();
    return () => {
      controller.abort();
      setQuality(null);
    };
  }, [videoRef, enabled]);

  return enabled ? quality : null;
}
