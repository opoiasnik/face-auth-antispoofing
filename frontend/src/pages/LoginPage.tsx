import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { authApi, type CaptureBody } from "@/api/endpoints";
import { useAuth } from "@/auth/context";
import { BiometricCapture } from "@/components/BiometricCapture";
import { Button, Field } from "@/components/ui";

export function LoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [faceOnly, setFaceOnly] = useState(false);
  const [username, setUsername] = useState("");
  const normalized = username.trim().toLowerCase();
  const redirectTo = (location.state as { from?: string } | null)?.from ?? "/dashboard";

  const capture = async (body: CaptureBody) => {
    const response = faceOnly
      ? await authApi.identify(body)
      : await authApi.verify({ ...body, username: normalized });
    signIn(response);
    navigate(redirectTo, { replace: true });
  };

  return (
    <div className="flow">
      <h1>Prihlásenie</h1>
      {faceOnly ? (
        <p className="flow__note">Nájdeme vás iba podľa tváre.</p>
      ) : (
        <Field
          label="Používateľské meno"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          autoFocus
        />
      )}
      <Button variant="link" className="flow__switch" onClick={() => setFaceOnly((v) => !v)}>
        {faceOnly ? "Prihlásiť sa s menom" : "Prihlásiť sa bez mena"}
      </Button>

      <BiometricCapture
        purpose="authenticate"
        submitLabel="Prihlásiť sa"
        onCapture={capture}
        canStart={faceOnly || normalized.length >= 3}
        blockedHint="Zadajte používateľské meno"
      />

      <p className="flow__footer">
        Nemáte účet? <Link to="/enroll">Vytvoriť účet</Link>
      </p>
    </div>
  );
}
