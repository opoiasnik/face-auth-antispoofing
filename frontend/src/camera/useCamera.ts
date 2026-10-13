import { useCallback, useEffect, useRef, useState } from "react";

export type CameraStatus = "idle" | "starting" | "ready" | "error";

const CONSTRAINTS: MediaStreamConstraints = {
  audio: false,
  video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
};

function describeError(error: unknown): string {
  if (!window.isSecureContext) return "Kamera vyžaduje zabezpečené pripojenie (HTTPS alebo localhost).";
  if (error instanceof DOMException) {
    switch (error.name) {
      case "NotAllowedError":
        return "Prístup ku kamere bol zamietnutý. Povoľte ho v nastaveniach prehliadača.";
      case "NotFoundError":
      case "OverconstrainedError":
        return "Nebola nájdená žiadna vhodná kamera.";
      case "NotReadableError":
        return "Kameru práve používa iná aplikácia.";
    }
  }
  return "Kameru sa nepodarilo spustiť.";
}

export function useCamera() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const attemptRef = useRef(0);
  const [status, setStatus] = useState<CameraStatus>("idle");
  const [error, setError] = useState<string | null>(null);

  const release = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
  }, []);

  const stop = useCallback(() => {
    attemptRef.current += 1;
    release();
    setStatus("idle");
  }, [release]);

  const start = useCallback(async () => {
    if (streamRef.current) return;
    const attempt = ++attemptRef.current;
    setStatus("starting");
    setError(null);
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error("unsupported");
      const stream = await navigator.mediaDevices.getUserMedia(CONSTRAINTS);
      if (attempt !== attemptRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = stream;
      const video = videoRef.current;
      if (video) {
        video.srcObject = stream;
        await video.play().catch((err: unknown) => {
          if (!(err instanceof DOMException && err.name === "AbortError")) throw err;
        });
      }
      if (attempt === attemptRef.current) setStatus("ready");
    } catch (err) {
      if (attempt !== attemptRef.current) return;
      release();
      setError(describeError(err));
      setStatus("error");
    }
  }, [release]);

  useEffect(() => stop, [stop]);

  return { videoRef, status, error, start, stop };
}
