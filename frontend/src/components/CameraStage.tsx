import { useId, type RefObject } from "react";

import type { QualityCheck } from "@/api/types";
import type { CaptureProgress } from "@/biometrics/useLivenessCapture";
import { ACTION_LABELS, QUALITY_HINTS } from "@/biometrics/messages";

interface Props {
  videoRef: RefObject<HTMLVideoElement | null>;
  progress: CaptureProgress;
  quality: QualityCheck | null;
  cameraReady: boolean;
}

/** Mirrored camera preview with a face guide, challenge instruction and step indicator. */
export function CameraStage({ videoRef, progress, quality, cameraReady }: Props) {
  // useId() contains characters (":" / "«") that are not valid inside url(#…)
  const maskId = `face-hole-${useId().replace(/[^\w-]/g, "")}`;
  const action = progress.phase === "capturing" ? progress.actions[progress.step] : undefined;
  const label = action ? ACTION_LABELS[action] : undefined;
  const guideState =
    progress.phase === "capturing" ? "active" : quality ? (quality.ok ? "ok" : "warn") : "idle";

  return (
    <div className="stage">
      <video ref={videoRef} className="stage__video" playsInline muted autoPlay aria-label="Náhľad kamery" />
      {!cameraReady && <div className="stage__placeholder">Kamera je vypnutá</div>}

      <svg className={`stage__guide stage__guide--${guideState}`} viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden>
        <defs>
          <mask id={maskId}>
            <rect width="100" height="100" fill="white" />
            <ellipse cx="50" cy="47" rx="21" ry="34" fill="black" />
          </mask>
        </defs>
        <rect width="100" height="100" className="stage__shade" mask={`url(#${maskId})`} />
        <ellipse cx="50" cy="47" rx="21" ry="34" className="stage__oval" vectorEffect="non-scaling-stroke" />
      </svg>

      {label && (
        <div className="stage__prompt" aria-live="assertive">
          <span className="stage__icon">{label.icon}</span>
          <span>{label.text}</span>
          <div className="stage__bar">
            <div style={{ width: `${Math.round(progress.stepProgress * 100)}%` }} />
          </div>
        </div>
      )}

      {progress.phase === "idle" && cameraReady && quality && (
        <div className={`stage__status ${quality.ok ? "is-ok" : "is-warn"}`} aria-live="polite">
          {quality.ok ? "Tvár je pripravená" : quality.issues.map((i) => QUALITY_HINTS[i]).join(" · ")}
        </div>
      )}

      {progress.phase === "capturing" && (
        <ol className="stage__steps" aria-label="Kroky výzvy">
          {progress.actions.map((a, i) => (
            <li key={a} className={i < progress.step ? "done" : i === progress.step ? "current" : ""}>
              {ACTION_LABELS[a].icon}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
