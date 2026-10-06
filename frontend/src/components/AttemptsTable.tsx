import type { Attempt } from "@/api/types";
import { formatDate, formatScore, MODE_LABELS, REASON_LABELS } from "@/lib/format";

import { Badge } from "./ui";

export function AttemptsTable({ attempts, showUser = false }: { attempts: Attempt[]; showUser?: boolean }) {
  if (attempts.length === 0) return <p className="muted">Zatiaľ žiadne záznamy.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Čas</th>
            {showUser && <th>Používateľ</th>}
            <th>Operácia</th>
            <th>Výsledok</th>
            <th title="Kosínusová podobnosť so vzorom">Zhoda</th>
            <th title="Skóre pasívnej detekcie živosti">Živosť</th>
            <th>Výzva</th>
            <th>Čas [ms]</th>
            {showUser && <th>IP</th>}
          </tr>
        </thead>
        <tbody>
          {attempts.map((a) => (
            <tr key={a.id}>
              <td>{formatDate(a.created_at)}</td>
              {showUser && <td>{a.username ?? "–"}</td>}
              <td>{MODE_LABELS[a.mode] ?? a.mode}</td>
              <td>
                {a.success ? (
                  <Badge tone="success">úspech</Badge>
                ) : (
                  <Badge tone="error">{REASON_LABELS[a.failure_reason ?? ""] ?? a.failure_reason}</Badge>
                )}
              </td>
              <td>{formatScore(a.match_score)}</td>
              <td>{formatScore(a.passive_score)}</td>
              <td>{a.active_passed === null ? "–" : a.active_passed ? "✓" : "✗"}</td>
              <td>{a.duration_ms}</td>
              {showUser && <td>{a.client_ip ?? "–"}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
