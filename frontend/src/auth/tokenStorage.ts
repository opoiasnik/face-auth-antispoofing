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
      return;
    }
  },
  clear(): void {
    current = null;
    try {
      sessionStorage.removeItem(KEY);
    } catch {
      return;
    }
  },
};

export const UNAUTHORIZED_EVENT = "faceauth:unauthorized";
