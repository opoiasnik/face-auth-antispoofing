export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

/** Frames are downscaled before upload – enough for detection, small payload. */
export const CAPTURE_MAX_WIDTH = 640;
export const CAPTURE_JPEG_QUALITY = 0.9;

/** Pre-flight quality check cadence while the user positions their face. */
export const QUALITY_POLL_MS = 1200;
export const QUALITY_MAX_WIDTH = 480;
