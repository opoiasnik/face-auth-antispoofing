import { request } from "./http";
import type {
  Attempt,
  AuthResponse,
  Challenge,
  ChallengePurpose,
  Frame,
  QualityCheck,
  Stats,
  User,
} from "./types";

export interface CaptureBody {
  challenge_id: string;
  frames: Frame[];
}

export const biometricsApi = {
  createChallenge: (purpose: ChallengePurpose, signal?: AbortSignal) =>
    request<Challenge>("/challenges", { method: "POST", body: { purpose }, signal }),
  checkQuality: (image: string, signal?: AbortSignal) =>
    request<QualityCheck>("/biometrics/quality", { method: "POST", body: { image }, signal }),
};

export const authApi = {
  enroll: (body: CaptureBody & { username: string; full_name?: string | null }) =>
    request<AuthResponse>("/enrollment", { method: "POST", body }),
  verify: (body: CaptureBody & { username: string }) =>
    request<AuthResponse>("/auth/verify", { method: "POST", body }),
  identify: (body: CaptureBody) => request<AuthResponse>("/auth/identify", { method: "POST", body }),
};

export const accountApi = {
  me: () => request<User>("/users/me"),
  attempts: (limit = 20) => request<Attempt[]>(`/users/me/attempts?limit=${limit}`),
  reenroll: (body: CaptureBody) => request<AuthResponse>("/users/me/face", { method: "PUT", body }),
  remove: () => request<void>("/users/me", { method: "DELETE" }),
};

export const adminApi = {
  stats: () => request<Stats>("/admin/stats"),
  users: () => request<User[]>("/admin/users?limit=200"),
  attempts: (limit = 100) => request<Attempt[]>(`/admin/attempts?limit=${limit}`),
  setActive: (userId: number, active: boolean) =>
    request<User>(`/admin/users/${userId}/active?active=${active}`, { method: "PATCH" }),
  removeUser: (userId: number) => request<void>(`/admin/users/${userId}`, { method: "DELETE" }),
};
