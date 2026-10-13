import { useEffect, useState, type RefObject } from "react";

import { biometricsApi } from "@/api/endpoints";
import type { QualityCheck } from "@/api/types";
import { captureFrame } from "@/camera/frames";
import { QUALITY_MAX_WIDTH, QUALITY_POLL_MS } from "@/config";

import { sleep } from "./schedule";

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
          const image = captureFrame(video, QUALITY_MAX_WIDTH, 0.8);
          const result = await biometricsApi.checkQuality(image, controller.signal).catch(() => null);
          if (result) setQuality(result);
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
