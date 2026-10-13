import type { RefObject } from "react";

import type { ChallengeAction } from "@/api/types";

export type ScannerState = "idle" | "ready" | "scanning" | "verifying" | "error";

interface Props {
  videoRef: RefObject<HTMLVideoElement | null>;
  cameraReady: boolean;
  state: ScannerState;
  progress: number;
  direction?: ChallengeAction | null;
}

const TICKS = 90;
const TICK_ANGLES = Array.from({ length: TICKS }, (_, i) => (i / TICKS) * 360);

export function FaceScanner({ videoRef, cameraReady, state, progress, direction }: Props) {
  const filled = Math.round(progress * TICKS);
  return (
    <div className={`scanner scanner--${state}`}>
      <svg className="scanner__ring" viewBox="0 0 100 100" aria-hidden>
        {TICK_ANGLES.map((angle, i) => (
          <line
            key={angle}
            x1="50"
            y1="1.5"
            x2="50"
            y2="5"
            transform={`rotate(${angle} 50 50)`}
            className={i < filled ? "tick tick--on" : "tick"}
          />
        ))}
      </svg>
      <div className="scanner__lens">
        <video ref={videoRef} playsInline muted autoPlay aria-label="Náhľad kamery" />
        {!cameraReady && <span className="scanner__off">Kamera je vypnutá</span>}
        {direction && direction !== "center" && (
          <svg className={`scanner__hint scanner__hint--${direction}`} viewBox="0 0 24 24" aria-hidden>
            <path d="M15 5l-7 7 7 7" />
          </svg>
        )}
      </div>
    </div>
  );
}
