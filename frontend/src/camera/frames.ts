import { CAPTURE_JPEG_QUALITY, CAPTURE_MAX_WIDTH } from "@/config";

let canvas: HTMLCanvasElement | null = null;

/**
 * Grab the current video frame as a base64 JPEG (without the data-URL prefix).
 * The frame is NOT mirrored – the server expects the raw camera image.
 */
export function captureFrame(
  video: HTMLVideoElement,
  maxWidth = CAPTURE_MAX_WIDTH,
  quality = CAPTURE_JPEG_QUALITY,
): string {
  const { videoWidth, videoHeight } = video;
  if (!videoWidth || !videoHeight) throw new Error("Video stream is not ready");
  const scale = Math.min(1, maxWidth / videoWidth);
  canvas ??= document.createElement("canvas");
  canvas.width = Math.round(videoWidth * scale);
  canvas.height = Math.round(videoHeight * scale);
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Canvas 2D context unavailable");
  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  const dataUrl = canvas.toDataURL("image/jpeg", quality);
  return dataUrl.slice(dataUrl.indexOf(",") + 1);
}
