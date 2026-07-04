from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Optional


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS proposals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  exchange TEXT NOT NULL,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  side TEXT NOT NULL,
  rationale TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  decided_at TEXT,
  decision_note TEXT,
  suggested_entry REAL,
  suggested_stop REAL,
  suggested_take_profit REAL,
  risk_pct REAL
);

CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals(status);
CREATE INDEX IF NOT EXISTS idx_proposals_symbol ON proposals(symbol);
"""


@dataclass(frozen=True)
class Proposal:
    id: int
    created_at: str
    exchange: str
    symbol: str
    timeframe: str
    side: str
    rationale: str
    status: str
    decided_at: Optional[str]
    decision_note: Optional[str]
    suggested_entry: Optional[float]
    suggested_stop: Optional[float]
    suggested_take_profit: Optional[float]
    risk_pct: Optional[float]


@contextmanager
def connect(db_path: str) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    finally:
        conn.close()


def _try_add_column(conn: sqlite3.Connection, table: str, col_def: str) -> None:
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
    except sqlite3.OperationalError:
        # Column likely exists already.
        return


def init_db(db_path: str) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        # Lightweight migrations for early iterations.
        _try_add_column(conn, "proposals", "decided_at TEXT")
        _try_add_column(conn, "proposals", "decision_note TEXT")


def insert_proposal(
    db_path: str,
    *,
    created_at: str,
    exchange: str,
    symbol: str,
    timeframe: str,
    side: str,
    rationale: str,
    suggested_entry: Optional[float] = None,
    suggested_stop: Optional[float] = None,
    suggested_take_profit: Optional[float] = None,
    risk_pct: Optional[float] = None,
) -> int:
    with connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO proposals (
              created_at, exchange, symbol, timeframe, side, rationale, suggested_entry, suggested_stop, suggested_take_profit, risk_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                exchange,
                symbol,
                timeframe,
                side,
                rationale,
                suggested_entry,
                suggested_stop,
                suggested_take_profit,
                risk_pct,
            ),
        )
        return int(cur.lastrowid)


def get_proposal(db_path: str, proposal_id: int) -> Optional[Proposal]:
    with connect(db_path) as conn:
        r = conn.execute("SELECT * FROM proposals WHERE id = ?", (proposal_id,)).fetchone()
        if r is None:
            return None

        return Proposal(
            id=int(r["id"]),
            created_at=str(r["created_at"]),
            exchange=str(r["exchange"]),
            symbol=str(r["symbol"]),
            timeframe=str(r["timeframe"]),
            side=str(r["side"]),
            rationale=str(r["rationale"]),
            status=str(r["status"]),
            decided_at=r["decided_at"],
            decision_note=r["decision_note"],
            suggested_entry=r["suggested_entry"],
            suggested_stop=r["suggested_stop"],
            suggested_take_profit=r["suggested_take_profit"],
            risk_pct=r["risk_pct"],
        )


def decide_proposal(
    db_path: str,
    *,
    proposal_id: int,
    status: str,
    decided_at: str,
    decision_note: Optional[str] = None,
) -> bool:
    if status not in ("approved", "rejected"):
        raise ValueError("status must be 'approved' or 'rejected'")

    with connect(db_path) as conn:
        cur = conn.execute(
            """
            UPDATE proposals
            SET status = ?, decided_at = ?, decision_note = ?
            WHERE id = ? AND status = 'pending'
            """,
            (status, decided_at, decision_note, proposal_id),
        )
        return cur.rowcount == 1


def list_proposals(db_path: str, status: str = "pending") -> list[Proposal]:
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM proposals WHERE status = ? ORDER BY created_at DESC", (status,)
        ).fetchall()

    return [
        Proposal(
            id=int(r["id"]),
            created_at=str(r["created_at"]),
            exchange=str(r["exchange"]),
            symbol=str(r["symbol"]),
            timeframe=str(r["timeframe"]),
            side=str(r["side"]),
            rationale=str(r["rationale"]),
            status=str(r["status"]),
            decided_at=r["decided_at"],
            decision_note=r["decision_note"],
            suggested_entry=r["suggested_entry"],
            suggested_stop=r["suggested_stop"],
            suggested_take_profit=r["suggested_take_profit"],
            risk_pct=r["risk_pct"],
        )
        for r in rows
    ]
