import { useCallback, useMemo, useState } from "react";

import { adminApi } from "@/api/endpoints";
import type { Stats, User } from "@/api/types";
import { useAuth } from "@/auth/context";
import { describeError } from "@/biometrics/messages";
import { AttemptsTable } from "@/components/AttemptsTable";
import { Alert, Badge, Button, Card, Spinner } from "@/components/ui";
import { formatDate, MODE_LABELS, REASON_LABELS } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";

function summarize(stats: Stats) {
  const byMode = new Map<string, { total: number; success: number }>();
  const reasons = new Map<string, number>();
  for (const bucket of stats.attempts) {
    const entry = byMode.get(bucket.mode) ?? { total: 0, success: 0 };
    entry.total += bucket.count;
    if (bucket.success) entry.success += bucket.count;
    else reasons.set(bucket.failure_reason ?? "?", (reasons.get(bucket.failure_reason ?? "?") ?? 0) + bucket.count);
    byMode.set(bucket.mode, entry);
  }
  return { byMode: [...byMode.entries()], reasons: [...reasons.entries()].sort((a, b) => b[1] - a[1]) };
}

export function AdminPage() {
  const { user: me } = useAuth();
  const loader = useCallback(
    () => Promise.all([adminApi.stats(), adminApi.users(), adminApi.attempts(100)]),
    [],
  );
  const { data, error, loading, reload } = useAsync(loader);
  const [actionError, setActionError] = useState<unknown>(null);
  const summary = useMemo(() => (data ? summarize(data[0]) : null), [data]);

  const act = async (fn: () => Promise<unknown>) => {
    setActionError(null);
    try {
      await fn();
      reload();
    } catch (err) {
      setActionError(err);
    }
  };

  const remove = (user: User) => {
    if (window.confirm(`Odstrániť používateľa ${user.username}?`)) void act(() => adminApi.removeUser(user.id));
  };

  if (loading && !data) return <Spinner label="Načítavam…" />;
  if (error) return <Alert tone="error">{describeError(error)}</Alert>;
  if (!data || !summary) return null;
  const [stats, users, attempts] = data;

  return (
    <div className="stack">
      {actionError !== null && <Alert tone="error">{describeError(actionError)}</Alert>}
      <div className="tiles">
        <div className="tile">
          <span className="tile__value">{stats.users}</span>
          <span className="tile__label">používateľov</span>
        </div>
        {summary.byMode.map(([mode, { total, success }]) => (
          <div className="tile" key={mode}>
            <span className="tile__value">{total ? Math.round((success / total) * 100) : 0} %</span>
            <span className="tile__label">
              {MODE_LABELS[mode] ?? mode} · {success}/{total}
            </span>
          </div>
        ))}
      </div>

      <div className="grid-2">
        <Card title="Používatelia">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Meno</th>
                  <th>Registrovaný</th>
                  <th>Stav</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>
                      {u.username} {u.is_admin && <Badge tone="neutral">admin</Badge>}
                    </td>
                    <td>{formatDate(u.created_at)}</td>
                    <td>{u.is_active ? <Badge tone="success">aktívny</Badge> : <Badge tone="error">blokovaný</Badge>}</td>
                    <td className="row-actions">
                      {u.id !== me?.id && (
                        <>
                          <Button variant="ghost" onClick={() => void act(() => adminApi.setActive(u.id, !u.is_active))}>
                            {u.is_active ? "Blokovať" : "Odblokovať"}
                          </Button>
                          <Button variant="ghost" onClick={() => remove(u)}>
                            Odstrániť
                          </Button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <Card title="Dôvody zamietnutia">
          {summary.reasons.length === 0 ? (
            <p className="muted">Žiadne zamietnuté pokusy.</p>
          ) : (
            <ul className="bars">
              {summary.reasons.map(([reason, count]) => (
                <li key={reason}>
                  <span>{REASON_LABELS[reason] ?? reason}</span>
                  <span className="bars__track">
                    <span style={{ width: `${(count / summary.reasons[0]![1]) * 100}%` }} />
                  </span>
                  <span>{count}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card
        title="Audit prihlásení"
        actions={
          <Button variant="ghost" onClick={reload}>
            Obnoviť
          </Button>
        }
      >
        <AttemptsTable attempts={attempts} showUser />
      </Card>
    </div>
  );
}
