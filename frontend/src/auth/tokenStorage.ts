// Access token kept in memory and mirrored to sessionStorage, so it survives a
// page reload but disappears when the browser tab is closed.
const KEY = "faceauth.token";

function read(): string | null {
  try {
    return sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
}

let current: string | null = read();

export const tokenStorage = {
  get(): string | null {
    return current;
  },
  set(token: string): void {
    current = token;
    try {
      sessionStorage.setItem(KEY, token);
    } catch {
      /* storage unavailable (private mode) – keep in memory only */
    }
  },
  clear(): void {
    current = null;
    try {
      sessionStorage.removeItem(KEY);
    } catch {
      /* ignore */
    }
  },
};

/** Dispatched by the HTTP layer when the server rejects the stored token. */
export const UNAUTHORIZED_EVENT = "faceauth:unauthorized";
