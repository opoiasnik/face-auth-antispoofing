import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";

import { accountApi, type CaptureBody } from "@/api/endpoints";
import { useAuth } from "@/auth/context";
import { describeError } from "@/biometrics/messages";
import { AttemptsTable } from "@/components/AttemptsTable";
import { BiometricCapture } from "@/components/BiometricCapture";
import { Button, Notice, Section, Spinner } from "@/components/ui";
import { formatDay } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";

export function DashboardPage() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const loadAttempts = useCallback(() => accountApi.attempts(20), []);
  const attempts = useAsync(loadAttempts);
  const [reenrolling, setReenrolling] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);

  if (!user) return null;

  const reenroll = async (body: CaptureBody) => {
    await accountApi.reenroll(body);
    setReenrolling(false);
    setNotice("Vzor tváre bol aktualizovaný.");
    attempts.reload();
  };

  const removeAccount = async () => {
    if (!window.confirm("Naozaj zmazať účet aj vzor tváre? Túto akciu nemožno vrátiť.")) return;
    try {
      await accountApi.remove();
      signOut();
      navigate("/", { replace: true });
    } catch (err) {
      setError(err);
    }
  };

  if (reenrolling) {
    return (
      <div className="flow">
        <h1>Aktualizovať tvár</h1>
        <p className="flow__note">Nový vzor sa uloží, iba ak ide o tú istú osobu.</p>
        <BiometricCapture purpose="enroll" submitLabel="Začať" onCapture={reenroll} />
        <Button variant="link" className="flow__switch" onClick={() => setReenrolling(false)}>
          Zrušiť
        </Button>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page__head">
        <h1>{user.full_name || user.username}</h1>
        <p className="muted">
          @{user.username} · účet od {formatDay(user.created_at)}
        </p>
      </header>

      {notice && <Notice tone="success">{notice}</Notice>}
      {error !== null && <Notice tone="error">{describeError(error)}</Notice>}

      <div className="row">
        <Button variant="secondary" onClick={() => setReenrolling(true)}>
          Aktualizovať tvár
        </Button>
        <Button variant="danger" onClick={() => void removeAccount()}>
          Zmazať účet
        </Button>
      </div>

      <Section
        title="Posledné prihlásenia"
        actions={
          <Button variant="link" onClick={attempts.reload}>
            Obnoviť
          </Button>
        }
      >
        {attempts.loading && !attempts.data ? (
          <Spinner />
        ) : attempts.error ? (
          <Notice tone="error">{describeError(attempts.error)}</Notice>
        ) : (
          <AttemptsTable attempts={attempts.data ?? []} />
        )}
      </Section>
    </div>
  );
}
