// Mirrors the backend schemas (backend/app/schemas).

export type ChallengePurpose = "enroll" | "authenticate";
export type ChallengeAction = "center" | "turn_left" | "turn_right" | "look_up" | "look_down";

export type QualityIssue =
  | "no_face"
  | "multiple_faces"
  | "face_too_small"
  | "too_blurry"
  | "too_dark"
  | "too_bright";

export type RejectionReason =
  | "quality"
  | "passive_spoof"
  | "active_challenge_failed"
  | "identity_inconsistent"
  | "no_match"
  | "duplicate_face";

export interface CaptureParameters {
  frames_per_step: number;
  step_duration_ms: number;
  lead_in_ms: number;
}

export interface Challenge {
  challenge_id: string;
  purpose: ChallengePurpose;
  actions: ChallengeAction[];
  expires_in: number;
  capture: CaptureParameters;
}

export interface Frame {
  step: number;
  image: string;
}

export interface QualityCheck {
  ok: boolean;
  issues: QualityIssue[];
  face_size: number;
  sharpness: number;
  brightness: number;
}

export interface User {
  id: number;
  username: string;
  full_name: string | null;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

export interface LivenessSummary {
  passive_liveness: number | null;
  active_liveness: {
    passed: boolean;
    steps: { action: ChallengeAction; passed: boolean; usable_frames: number; peak_delta: number }[];
  } | null;
  consistency: number | null;
  quality_issues: Partial<Record<QualityIssue, number>>;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
  match_score: number | null;
  liveness: LivenessSummary | null;
}

export interface Attempt {
  id: number;
  user_id: number | null;
  username: string | null;
  mode: "enroll" | "reenroll" | "verify" | "identify";
  success: boolean;
  failure_reason: string | null;
  match_score: number | null;
  passive_score: number | null;
  active_passed: boolean | null;
  frames: number;
  duration_ms: number;
  client_ip: string | null;
  created_at: string;
}

export interface Stats {
  users: number;
  attempts: { mode: string; success: boolean; failure_reason: string | null; count: number }[];
}
