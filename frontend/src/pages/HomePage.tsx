import { Link } from "react-router-dom";

import { useAuth } from "@/auth/context";

export function HomePage() {
  const { user } = useAuth();
  return (
    <div className="home">
      <h1>Prihlásenie tvárou.</h1>
      <p className="lead">
        Bez hesla, iba webkamera. Fotka ani video na mobile vás nenahradia.
      </p>
      <div className="home__actions">
        {user ? (
          <Link className="btn btn--primary" to="/dashboard">
            Môj účet
          </Link>
        ) : (
          <>
            <Link className="btn btn--primary" to="/login">
              Prihlásiť sa
            </Link>
            <Link className="btn btn--secondary" to="/enroll">
              Vytvoriť účet
            </Link>
          </>
        )}
      </div>

      <dl className="facts">
        <div>
          <dt>Ako to funguje</dt>
          <dd>Pozriete sa do kamery a urobíte pár krátkych pohybov hlavou. Trvá to asi 5 sekúnd.</dd>
        </div>
        <div>
          <dt>Ochrana pred podvrhom</dt>
          <dd>Neurónová sieť rozpozná fotku a obrazovku, náhodné pohyby zas vopred nahrané video.</dd>
        </div>
        <div>
          <dt>Vaše údaje</dt>
          <dd>Fotky neukladáme. Uchováva sa iba zašifrovaný vzor tváre, ktorý môžete kedykoľvek zmazať.</dd>
        </div>
      </dl>
    </div>
  );
}
