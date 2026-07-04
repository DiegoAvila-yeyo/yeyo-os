from __future__ import annotations

import argparse
from datetime import datetime, timezone

from rich.console import Console
from rich.table import Table

from trading_lab.config import load_config
from trading_lab.db import (
    decide_proposal,
    get_proposal,
    init_db,
    insert_proposal,
    list_proposals,
)
from trading_lab.exchanges.ccxt_client import make_public_exchange
from trading_lab.strategies.trend_follow_v1 import compute_signal


console = Console()


DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT"]


def cmd_init_db() -> int:
    cfg = load_config()
    init_db(cfg.db_path)
    console.print(f"DB initialized: {cfg.db_path}")
    return 0


def cmd_scan(exchange: str, timeframe: str, limit: int) -> int:
    cfg = load_config()
    init_db(cfg.db_path)

    ex = make_public_exchange(exchange).client

    created = 0
    for symbol in DEFAULT_SYMBOLS:
        try:
            ohlcv = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            sig = compute_signal(ohlcv)
            if sig.side != "none":
                pid = insert_proposal(
                    cfg.db_path,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    exchange=exchange,
                    symbol=symbol,
                    timeframe=timeframe,
                    side=sig.side,
                    rationale=sig.rationale,
                )
                created += 1
                console.print(f"Created proposal #{pid} for {symbol}: {sig.rationale}")
            else:
                console.print(f"{symbol}: {sig.rationale}")
        except Exception as e:
            console.print(f"[red]Error scanning {symbol} on {exchange}: {e}[/red]")

    console.print(f"Scan complete. New proposals: {created}")
    return 0


def cmd_list(status: str) -> int:
    cfg = load_config()
    init_db(cfg.db_path)
    props = list_proposals(cfg.db_path, status=status)

    table = Table(title=f"Proposals ({status})")
    table.add_column("id", style="cyan", no_wrap=True)
    table.add_column("created_at")
    table.add_column("exchange")
    table.add_column("symbol")
    table.add_column("tf")
    table.add_column("side")
    table.add_column("status")
    table.add_column("decided_at")
    table.add_column("rationale")

    for p in props:
        table.add_row(
            str(p.id),
            p.created_at,
            p.exchange,
            p.symbol,
            p.timeframe,
            p.side,
            p.status,
            p.decided_at or "",
            p.rationale,
        )

    console.print(table)
    return 0


def cmd_decide(proposal_id: int, status: str, note: str | None) -> int:
    cfg = load_config()
    init_db(cfg.db_path)

    p = get_proposal(cfg.db_path, proposal_id)
    if p is None:
        console.print(f"[red]Proposal not found: {proposal_id}[/red]")
        return 2

    ok = decide_proposal(
        cfg.db_path,
        proposal_id=proposal_id,
        status=status,
        decided_at=datetime.now(timezone.utc).isoformat(),
        decision_note=note,
    )
    if not ok:
        console.print(f"[yellow]Proposal #{proposal_id} is not pending (current: {p.status}).[/yellow]")
        return 1

    console.print(f"Proposal #{proposal_id} marked as {status}.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="trading-lab")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init-db")

    scan = sub.add_parser("scan")
    scan.add_argument("--exchange", default=load_config().default_exchange)
    scan.add_argument("--timeframe", default="1d")
    scan.add_argument("--limit", type=int, default=250)

    ls = sub.add_parser("list-proposals")
    ls.add_argument("--status", default="pending")

    approve = sub.add_parser("approve")
    approve.add_argument("proposal_id", type=int)
    approve.add_argument("--note")

    reject = sub.add_parser("reject")
    reject.add_argument("proposal_id", type=int)
    reject.add_argument("--note")

    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.cmd == "init-db":
        return cmd_init_db()
    if args.cmd == "scan":
        return cmd_scan(exchange=args.exchange, timeframe=args.timeframe, limit=args.limit)
    if args.cmd == "list-proposals":
        return cmd_list(status=args.status)
    if args.cmd == "approve":
        return cmd_decide(args.proposal_id, "approved", args.note)
    if args.cmd == "reject":
        return cmd_decide(args.proposal_id, "rejected", args.note)

    raise SystemExit(2)


if __name__ == "__main__":
    raise SystemExit(main())
