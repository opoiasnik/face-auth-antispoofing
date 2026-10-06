import { useCallback, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { accountApi, type CaptureBody } from "@/api/endpoints";
import { useAuth } from "@/auth/context";
import { describeError } from "@/biometrics/messages";
import { AttemptsTable } from "@/components/AttemptsTable";
import { BiometricCapture } from "@/components/BiometricCapture";
import { Alert, Button, Card, Spinner } from "@/components/ui";
import { formatDate } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";

export function DashboardPage() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const welcome = (location.state as { welcome?: boolean } | null)?.welcome ?? false;
  const loadAttempts = useCallback(() => accountApi.attempts(20), []);
  const attempts = useAsync(loadAttempts);
  const [reenrolling, setReenrolling] = useState(false);
  const [notice, setNotice] = useState<string | null>(welcome ? "Registrácia prebehla úspešne." : null);
  const [deleteError, setDeleteError] = useState<unknown>(null);

  if (!user) return null;

  const reenroll = async (body: CaptureBody) => {
    await accountApi.reenroll(body);
    setReenrolling(false);
    setNotice("Biometrický vzor bol aktualizovaný.");
    attempts.reload();
  };

  const removeAccount = async () => {
    if (!window.confirm("Naozaj chcete natrvalo odstrániť účet aj biometrický vzor?")) return;
    try {
      await accountApi.remove();
      signOut();
      navigate("/", { replace: true });
    } catch (err) {
      setDeleteError(err);
    }
  };

  return (
    <div className="stack">
      {notice && <Alert tone="success">{notice}</Alert>}
      <div className="grid-2">
        <Card title="Môj účet">
          <dl className="details">
            <dt>Používateľ</dt>
            <dd>{user.username}</dd>
            <dt>Meno</dt>
            <dd>{user.full_name ?? "–"}</dd>
            <dt>Rola</dt>
            <dd>{user.is_admin ? "administrátor" : "používateľ"}</dd>
            <dt>Registrovaný</dt>
            <dd>{formatDate(user.created_at)}</dd>
          </dl>
          <div className="row">
            <Button variant="secondary" onClick={() => setReenrolling((v) => !v)}>
              {reenrolling ? "Zavrieť" : "Aktualizovať vzor tváre"}
            </Button>
            <Button variant="danger" onClick={() => void removeAccount()}>
              Odstrániť účet
            </Button>
          </div>
          {deleteError !== null && <Alert tone="error">{describeError(deleteError)}</Alert>}
        </Card>
        {reenrolling && (
          <Card title="Nový vzor tváre">
            <BiometricCapture purpose="enroll" submitLabel="Uložiť nový vzor" onCapture={reenroll} />
          </Card>
        )}
      </div>
      <Card
        title="História prihlásení"
        actions={
          <Button variant="ghost" onClick={attempts.reload}>
            Obnoviť
          </Button>
        }
      >
        {attempts.loading && !attempts.data ? (
          <Spinner />
        ) : attempts.error ? (
          <Alert tone="error">{describeError(attempts.error)}</Alert>
        ) : (
          <AttemptsTable attempts={attempts.data ?? []} />
        )}
      </Card>
    </div>
  );
}
