import type { Attempt } from "@/api/types";
import { formatDate, formatScore, MODE_LABELS, REASON_LABELS } from "@/lib/format";

function Result({ attempt }: { attempt: Attempt }) {
  if (attempt.success) return <span className="result result--ok">Úspech</span>;
  const reason = attempt.failure_reason ?? "";
  return <span className="result result--fail">{REASON_LABELS[reason] ?? reason}</span>;
}

export function AttemptsTable({ attempts, detailed = false }: { attempts: Attempt[]; detailed?: boolean }) {
  if (attempts.length === 0) return <p className="muted">Zatiaľ žiadne záznamy.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Čas</th>
            {detailed && <th>Používateľ</th>}
            <th>Operácia</th>
            <th>Výsledok</th>
            {detailed && (
              <>
                <th title="Kosínusová podobnosť so vzorom">Zhoda</th>
                <th title="Skóre pasívnej detekcie živosti">Živosť</th>
                <th>ms</th>
                <th>IP</th>
              </>
            )}
          </tr>
        </thead>
        <tbody>
          {attempts.map((a) => (
            <tr key={a.id}>
              <td>{formatDate(a.created_at)}</td>
              {detailed && <td>{a.username ?? "–"}</td>}
              <td>{MODE_LABELS[a.mode] ?? a.mode}</td>
              <td>
                <Result attempt={a} />
              </td>
              {detailed && (
                <>
                  <td>{formatScore(a.match_score)}</td>
                  <td>{formatScore(a.passive_score)}</td>
                  <td>{a.duration_ms}</td>
                  <td>{a.client_ip ?? "–"}</td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
