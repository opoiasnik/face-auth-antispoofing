import { Link } from "react-router-dom";

import { useAuth } from "@/auth/context";

const LAYERS = [
  {
    title: "Kontrola kvality",
    text: "Detektor YuNet overí, že v zábere je práve jedna dostatočne veľká, ostrá a osvetlená tvár.",
  },
  {
    title: "Pasívna detekcia podvrhu",
    text: "Dvojica CNN MiniFASNet analyzuje textúru a kontext snímky – odhalí tlač, displej či video.",
  },
  {
    title: "Aktívna výzva",
    text: "Náhodná, jednorazová sekvencia pohybov hlavy, ktorú statická fotografia ani nahrávka nesplní.",
  },
  {
    title: "Konzistencia identity",
    text: "Všetky snímky relácie musia patriť tej istej osobe – zabraňuje výmene tváre počas snímania.",
  },
  {
    title: "Porovnanie vzorov",
    text: "Model SFace vytvorí 128-rozmerný vektor príznakov, ktorý sa porovná so zašifrovaným vzorom.",
  },
];

export function HomePage() {
  const { user } = useAuth();
  return (
    <div className="stack">
      <section className="hero">
        <h1>Biometrická autentifikácia tváre s ochranou proti falšovaniu</h1>
        <p className="lead">
          Prihlásenie bez hesla pomocou webkamery. Systém kombinuje rozpoznávanie tváre s viacvrstvovou
          detekciou prezentačných útokov (ISO/IEC 30107).
        </p>
        <div className="row">
          {user ? (
            <Link className="btn btn--primary" to="/dashboard">
              Prejsť do účtu
            </Link>
          ) : (
            <>
              <Link className="btn btn--primary" to="/login">
                Prihlásiť sa tvárou
              </Link>
              <Link className="btn btn--secondary" to="/enroll">
                Zaregistrovať sa
              </Link>
            </>
          )}
        </div>
      </section>
      <section>
        <h2>Vrstvy ochrany</h2>
        <ol className="layers">
          {LAYERS.map((layer) => (
            <li key={layer.title}>
              <strong>{layer.title}</strong>
              <span>{layer.text}</span>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
