import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "@/auth/context";

import { Button } from "./ui";

export function Layout() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  const logout = () => {
    signOut();
    navigate("/");
  };

  return (
    <div className="app">
      <header className="topbar">
        <NavLink to="/" className="brand">
          <img src="/favicon.svg" alt="" width={28} height={28} />
          FaceAuth
        </NavLink>
        <nav className="nav">
          {user ? (
            <>
              <NavLink to="/dashboard">Môj účet</NavLink>
              {user.is_admin && <NavLink to="/admin">Administrácia</NavLink>}
              <Button variant="ghost" onClick={logout}>
                Odhlásiť
              </Button>
            </>
          ) : (
            <>
              <NavLink to="/login">Prihlásenie</NavLink>
              <NavLink to="/enroll">Registrácia</NavLink>
            </>
          )}
        </nav>
      </header>
      <main className="content">
        <Outlet />
      </main>
      <footer className="footer muted small">
        Biometrická autentifikácia tváre s ochranou proti falšovaniu · semestrálny projekt BSB
      </footer>
    </div>
  );
}
