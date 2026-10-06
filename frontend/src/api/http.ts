import { API_BASE_URL } from "@/config";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }

  get reason(): string | undefined {
    const reason = this.details.reason;
    return typeof reason === "string" ? reason : undefined;
  }
}

type TokenProvider = () => string | null;
type UnauthorizedHandler = () => void;

let getToken: TokenProvider = () => null;
let onUnauthorized: UnauthorizedHandler = () => undefined;

/** Wired by the AuthProvider so that the HTTP layer stays framework-agnostic. */
export function configureAuth(provider: TokenProvider, unauthorized: UnauthorizedHandler): void {
  getToken = provider;
  onUnauthorized = unauthorized;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, signal } = options;
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(0, "network_error", "Server je nedostupný");
  }

  if (response.status === 204) return undefined as T;
  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const error = (payload as { error?: { code?: string; message?: string; details?: Record<string, unknown> } })
      ?.error;
    if (response.status === 401 && token && error?.code === "unauthorized") onUnauthorized();
    throw new ApiError(
      response.status,
      error?.code ?? "http_error",
      error?.message ?? response.statusText,
      error?.details ?? {},
    );
  }
  return payload as T;
}
