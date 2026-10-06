import { createContext, useContext } from "react";

import type { AuthResponse, User } from "@/api/types";

export interface AuthState {
  user: User | null;
  /** True while the stored session is being restored on page load. */
  initializing: boolean;
  signIn: (response: AuthResponse) => void;
  signOut: () => void;
  refresh: () => Promise<void>;
}

export const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}
