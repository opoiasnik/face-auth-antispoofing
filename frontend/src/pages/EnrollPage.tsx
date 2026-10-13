import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { authApi, type CaptureBody } from "@/api/endpoints";
import { useAuth } from "@/auth/context";
import { BiometricCapture } from "@/components/BiometricCapture";
import { Button, Field } from "@/components/ui";

const USERNAME_PATTERN = /^[a-z0-9._-]{3,32}$/;

export function EnrollPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [step, setStep] = useState<"details" | "face">("details");
  const normalized = username.trim().toLowerCase();
  const valid = USERNAME_PATTERN.test(normalized);

  const next = (event: FormEvent) => {
    event.preventDefault();
    if (valid) setStep("face");
  };

  const capture = async (body: CaptureBody) => {
    const response = await authApi.enroll({ ...body, username: normalized, full_name: fullName.trim() || null });
    signIn(response);
    navigate("/dashboard", { replace: true });
  };

  if (step === "face") {
    return (
      <div className="flow">
        <h1>Nastavenie tváre</h1>
        <p className="flow__note">Postupujte podľa pokynov pod kruhom.</p>
        <BiometricCapture purpose="enroll" submitLabel="Začať" onCapture={capture} />
        <Button variant="link" className="flow__switch" onClick={() => setStep("details")}>
          Späť
        </Button>
      </div>
    );
  }

  return (
    <form className="flow" onSubmit={next}>
      <h1>Nový účet</h1>
      <Field
        label="Používateľské meno"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        autoComplete="username"
        autoFocus
        hint="3–32 znakov: písmená, číslice, bodka, pomlčka"
        aria-invalid={username !== "" && !valid}
      />
      <Field
        label="Meno (nepovinné)"
        value={fullName}
        onChange={(e) => setFullName(e.target.value)}
        autoComplete="name"
        maxLength={128}
      />
      <Button type="submit" block disabled={!valid}>
        Pokračovať
      </Button>
      <p className="flow__fineprint">
        Pokračovaním súhlasíte so spracovaním vzoru tváre na prihlasovanie. Účet aj vzor môžete
        kedykoľvek zmazať.
      </p>
      <p className="flow__footer">
        Už máte účet? <Link to="/login">Prihlásiť sa</Link>
      </p>
    </form>
  );
}
