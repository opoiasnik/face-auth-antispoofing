import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { Spinner } from "@/components/ui";

import { useAuth } from "./context";

interface Props {
  children: ReactNode;
  admin?: boolean;
}

export function RequireAuth({ children, admin = false }: Props) {
  const { user, initializing } = useAuth();
  const location = useLocation();

  if (initializing) return <Spinner label="Obnovujem reláciu…" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (admin && !user.is_admin) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}
