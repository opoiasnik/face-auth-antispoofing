import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { authApi, type CaptureBody } from "@/api/endpoints";
import { useAuth } from "@/auth/context";
import { BiometricCapture } from "@/components/BiometricCapture";
import { Card, Field } from "@/components/ui";

type Mode = "verify" | "identify";

export function LoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState<Mode>("verify");
  const [username, setUsername] = useState("");
  const normalized = username.trim().toLowerCase();
  const redirectTo = (location.state as { from?: string } | null)?.from ?? "/dashboard";

  const capture = async (body: CaptureBody) => {
    const response =
      mode === "verify" ? await authApi.verify({ ...body, username: normalized }) : await authApi.identify(body);
    signIn(response);
    navigate(redirectTo, { replace: true });
  };

  return (
    <div className="grid-2">
      <Card title="Prihlásenie">
        <div className="segmented" role="tablist" aria-label="Spôsob prihlásenia">
          <button role="tab" aria-selected={mode === "verify"} onClick={() => setMode("verify")}>
            Meno + tvár (1:1)
          </button>
          <button role="tab" aria-selected={mode === "identify"} onClick={() => setMode("identify")}>
            Iba tvár (1:N)
          </button>
        </div>
        {mode === "verify" ? (
          <Field
            label="Používateľské meno"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
        ) : (
          <p className="muted">
            Systém vás vyhľadá medzi všetkými registrovanými používateľmi iba podľa tváre.
          </p>
        )}
        <p className="muted small">
          Nemáte účet? <Link to="/enroll">Zaregistrujte sa</Link>.
        </p>
      </Card>
      <Card title="Overenie tváre">
        <BiometricCapture
          purpose="authenticate"
          submitLabel="Prihlásiť sa"
          onCapture={capture}
          canStart={mode === "identify" || normalized.length >= 3}
        />
      </Card>
    </div>
  );
}
