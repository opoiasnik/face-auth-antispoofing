import { useEffect, useState } from "react";

import type { CaptureBody } from "@/api/endpoints";
import type { ChallengePurpose } from "@/api/types";
import { describeError, qualityHints } from "@/biometrics/messages";
import { useLivenessCapture } from "@/biometrics/useLivenessCapture";
import { useQualityMonitor } from "@/biometrics/useQualityMonitor";
import { useCamera } from "@/camera/useCamera";

import { CameraStage } from "./CameraStage";
import { Alert, Button } from "./ui";

interface Props {
  purpose: ChallengePurpose;
  submitLabel: string;
  /** Called with the captured challenge frames; should throw ApiError on rejection. */
  onCapture: (body: CaptureBody) => Promise<void>;
  /** Extra validation of the surrounding form before capture starts. */
  canStart?: boolean;
}

const PHASE_LABELS = {
  idle: "",
  challenge: "Pripravujem výzvu…",
  capturing: "Snímam…",
  verifying: "Overujem živosť a identitu…",
} as const;

export function BiometricCapture({ purpose, submitLabel, onCapture, canStart = true }: Props) {
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

  const hints = qualityHints(error);
  return (
    <div className="capture">
      <CameraStage
        videoRef={camera.videoRef}
        progress={progress}
        quality={quality}
        cameraReady={camera.status === "ready"}
      />

      {camera.error && (
        <Alert tone="error" title="Kamera">
          {camera.error}{" "}
          <Button variant="ghost" onClick={() => void camera.start()}>
            Skúsiť znova
          </Button>
        </Alert>
      )}

      {error !== null && (
        <Alert tone="error" title="Neúspešné">
          {describeError(error)}
          {hints.length > 0 && (
            <ul className="hints">
              {hints.map((hint) => (
                <li key={hint}>{hint}</li>
              ))}
            </ul>
          )}
        </Alert>
      )}

      <div className="capture__actions">
        {busy ? (
          <>
            <span className="muted">{PHASE_LABELS[progress.phase]}</span>
            {progress.phase === "capturing" && (
              <Button variant="secondary" onClick={cancel}>
                Zrušiť
              </Button>
            )}
          </>
        ) : (
          <Button onClick={() => void begin()} disabled={camera.status !== "ready" || !canStart}>
            {error ? "Skúsiť znova" : submitLabel}
          </Button>
        )}
      </div>
      <p className="muted small">
        Po spustení postupujte podľa pokynov na obrazovke (cca 7 s). Snímky sa spracujú na serveri
        a neukladajú sa – uchováva sa iba zašifrovaný biometrický vzor.
      </p>
    </div>
  );
}
