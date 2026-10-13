import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "@/auth/context";

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
        <Link to="/" className="wordmark">
          FaceAuth
        </Link>
        <nav className="nav">
          {user ? (
            <>
              <NavLink to="/dashboard">Účet</NavLink>
              {user.is_admin && <NavLink to="/admin">Správa</NavLink>}
              <button type="button" className="nav__button" onClick={logout}>
                Odhlásiť
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login">Prihlásiť</NavLink>
              <NavLink to="/enroll">Registrovať</NavLink>
            </>
          )}
        </nav>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
