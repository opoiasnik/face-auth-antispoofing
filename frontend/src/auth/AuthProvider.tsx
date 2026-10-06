import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { accountApi } from "@/api/endpoints";
import type { AuthResponse, User } from "@/api/types";

import { AuthContext, type AuthState } from "./context";
import { tokenStorage, UNAUTHORIZED_EVENT } from "./tokenStorage";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [initializing, setInitializing] = useState(() => tokenStorage.get() !== null);

  const signOut = useCallback(() => {
    tokenStorage.clear();
    setUser(null);
  }, []);

  const signIn = useCallback((response: AuthResponse) => {
    tokenStorage.set(response.access_token);
    setUser(response.user);
  }, []);

  const refresh = useCallback(async () => {
    if (tokenStorage.get()) setUser(await accountApi.me());
  }, []);

  // restore the session after a page reload
  useEffect(() => {
    if (!tokenStorage.get()) return;
    accountApi
      .me()
      .then(setUser)
      .catch(signOut)
      .finally(() => setInitializing(false));
  }, [signOut]);

  useEffect(() => {
    window.addEventListener(UNAUTHORIZED_EVENT, signOut);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, signOut);
  }, [signOut]);

  const value = useMemo<AuthState>(
    () => ({ user, initializing, signIn, signOut, refresh }),
    [user, initializing, signIn, signOut, refresh],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
