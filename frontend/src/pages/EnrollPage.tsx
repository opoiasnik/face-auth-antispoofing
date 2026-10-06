import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { authApi, type CaptureBody } from "@/api/endpoints";
import { useAuth } from "@/auth/context";
import { BiometricCapture } from "@/components/BiometricCapture";
import { Card, Field } from "@/components/ui";

const USERNAME_PATTERN = /^[a-z0-9._-]{3,32}$/;

export function EnrollPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const normalized = username.trim().toLowerCase();
  const valid = USERNAME_PATTERN.test(normalized);

  const capture = async (body: CaptureBody) => {
    const response = await authApi.enroll({ ...body, username: normalized, full_name: fullName.trim() || null });
    signIn(response);
    navigate("/dashboard", { replace: true, state: { welcome: true } });
  };

  return (
    <div className="grid-2">
      <Card title="Registrácia">
        <form className="stack" onSubmit={(e) => e.preventDefault()}>
          <Field
            label="Používateľské meno"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
            hint="3–32 znakov: malé písmená, číslice, bodka, pomlčka, podčiarkovník"
            aria-invalid={username !== "" && !valid}
          />
          <Field
            label="Celé meno (nepovinné)"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            autoComplete="name"
            maxLength={128}
          />
        </form>
        <p className="muted small">
          Registráciou súhlasíte so spracovaním biometrického vzoru tváre na účel prihlásenia (čl. 9
          GDPR). Účet aj vzor môžete kedykoľvek odstrániť. Už máte účet? <Link to="/login">Prihláste sa</Link>.
        </p>
      </Card>
      <Card title="Snímanie tváre">
        <BiometricCapture purpose="enroll" submitLabel="Zaregistrovať tvár" onCapture={capture} canStart={valid} />
      </Card>
    </div>
  );
}
