import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="stack center">
      <h1>404</h1>
      <p className="muted">Stránka neexistuje.</p>
      <Link to="/" className="btn btn--secondary">
        Späť na úvod
      </Link>
    </div>
  );
}
