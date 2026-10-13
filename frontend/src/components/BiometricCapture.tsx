import { useEffect, useState } from "react";

import type { CaptureBody } from "@/api/endpoints";
import type { ChallengePurpose } from "@/api/types";
import { ACTION_LABELS, describeError, QUALITY_HINTS, qualityHints } from "@/biometrics/messages";
import { useLivenessCapture } from "@/biometrics/useLivenessCapture";
import { useQualityMonitor } from "@/biometrics/useQualityMonitor";
import { useCamera } from "@/camera/useCamera";

import { FaceScanner, type ScannerState } from "./FaceScanner";
import { Button } from "./ui";

interface Props {
  purpose: ChallengePurpose;
  submitLabel: string;
  onCapture: (body: CaptureBody) => Promise<void>;
  canStart?: boolean;
  blockedHint?: string;
}

export function BiometricCapture({ purpose, submitLabel, onCapture, canStart = true, blockedHint }: Props) {
  const camera = useCamera();
  const { progress, run, cancel } = useLivenessCapture(camera.videoRef);
  const busy = progress.phase !== "idle";
  const quality = useQualityMonitor(camera.videoRef, camera.status === "ready" && !busy);
  const [error, setError] = useState<unknown>(null);

  const { start } = camera;
  useEffect(() => {
    void start();
  }, [start]);

  const begin = async () => {
    setError(null);
    try {
      await run(purpose, onCapture);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err);
    }
  };

  const action = progress.actions[progress.step];
  const total = progress.actions.length || 1;

  let state: ScannerState = "idle";
  let title: string;
  let subtitle = "";
  let ringProgress = 0;

  if (camera.status === "error") {
    title = "Kamera nie je dostupná";
    subtitle = camera.error ?? "";
  } else if (progress.phase === "challenge") {
    state = "scanning";
    title = "Pripravujem…";
  } else if (progress.phase === "capturing" && action) {
    state = "scanning";
    title = progress.stepDone ? "Výborne" : ACTION_LABELS[action];
    subtitle = `Krok ${progress.step + 1} z ${total}`;
    ringProgress = (progress.step + progress.stepProgress) / total;
  } else if (progress.phase === "verifying") {
    state = "verifying";
    title = "Overujem…";
    ringProgress = 1;
  } else if (error !== null) {
    state = "error";
    title = describeError(error);
    subtitle = qualityHints(error).join(" · ");
  } else if (!quality) {
    title = "Umiestnite tvár do kruhu";
  } else if (!quality.ok) {
    title = QUALITY_HINTS[quality.issues[0]!];
  } else {
    state = "ready";
    title = "Tvár je v poriadku";
  }
  if (!busy && !canStart && blockedHint && camera.status !== "error") subtitle = blockedHint;

  return (
    <div className="capture">
      <FaceScanner
        videoRef={camera.videoRef}
        cameraReady={camera.status === "ready"}
        state={state}
        progress={ringProgress}
        direction={progress.phase === "capturing" && !progress.stepDone ? action : null}
      />
      <div className="capture__text" aria-live="polite">
        <p className={state === "error" ? "capture__title capture__title--error" : "capture__title"}>
          {title}
        </p>
        <p className="capture__subtitle">{subtitle || " "}</p>
      </div>
      {camera.status === "error" ? (
        <Button block onClick={() => void camera.start()}>
          Povoliť kameru
        </Button>
      ) : busy ? (
        <Button block variant="secondary" onClick={cancel} disabled={progress.phase !== "capturing"}>
          Zrušiť
        </Button>
      ) : (
        <Button block onClick={() => void begin()} disabled={camera.status !== "ready" || !canStart}>
          {error ? "Skúsiť znova" : submitLabel}
        </Button>
      )}
    </div>
  );
}
