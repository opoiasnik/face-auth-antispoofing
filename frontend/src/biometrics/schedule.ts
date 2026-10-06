import type { CaptureParameters } from "@/api/types";

/**
 * Offsets (ms from the start of a step) at which frames are captured.
 * The first ``lead_in_ms`` give the user time to react to the instruction,
 * the remaining time is split evenly between the frames.
 */
export function captureOffsets({ frames_per_step, step_duration_ms, lead_in_ms }: CaptureParameters): number[] {
  const window = Math.max(step_duration_ms - lead_in_ms, 0);
  const interval = window / frames_per_step;
  return Array.from({ length: frames_per_step }, (_, i) => Math.round(lead_in_ms + interval * (i + 0.5)));
}

export function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(new DOMException("Aborted", "AbortError"));
    const timer = window.setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        window.clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}
