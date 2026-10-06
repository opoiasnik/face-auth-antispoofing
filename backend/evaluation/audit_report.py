"""Summarise real-world attempts stored in the audit log (end-to-end system test).

Usage::

    python -m evaluation.audit_report [--since 2026-11-01]
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime

import numpy as np
from sqlalchemy import select

from app.core.config import Settings
from app.db.models import AuthAttempt
from app.db.session import create_db_engine, create_session_factory
from evaluation import plots
from evaluation.common import markdown_table, output_dir, percent, write_json


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--since", type=datetime.fromisoformat, default=None)
    args = parser.parse_args()

    settings = Settings()
    factory = create_session_factory(create_db_engine(settings.database_url))
    stmt = select(AuthAttempt).order_by(AuthAttempt.created_at)
    if args.since:
        stmt = stmt.where(AuthAttempt.created_at >= args.since)
    with factory() as session:
        attempts = session.scalars(stmt).all()
    if not attempts:
        print("No attempts recorded yet")
        return 1

    by_mode: dict[str, list[AuthAttempt]] = defaultdict(list)
    for attempt in attempts:
        by_mode[attempt.mode].append(attempt)

    rows = []
    for mode, items in sorted(by_mode.items()):
        durations = [a.duration_ms for a in items]
        success = sum(a.success for a in items)
        rows.append(
            (
                mode,
                len(items),
                percent(success / len(items)),
                f"{np.mean(durations):.0f}",
                f"{np.percentile(durations, 95):.0f}",
            )
        )
    reasons = Counter(a.failure_reason for a in attempts if not a.success)

    out = output_dir(None, "audit")
    table = markdown_table(["Režim", "Pokusy", "Úspešnosť", "Priemer [ms]", "P95 [ms]"], rows)
    table += "\n" + markdown_table(["Dôvod zamietnutia", "Počet"], reasons.most_common())
    (out / "table.md").write_text(table, encoding="utf-8")
    write_json(
        out / "summary.json",
        {"attempts": len(attempts), "by_mode": {r[0]: r[1] for r in rows}, "reasons": reasons},
    )
    if reasons:
        plots.bar_chart(
            {str(k): float(v) for k, v in reasons.items()},
            out / "rejection_reasons",
            ylabel="Počet pokusov",
        )
    print(table)
    print(f"Results written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
