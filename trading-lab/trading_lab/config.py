from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Config:
    db_path: str
    default_exchange: str
    base_currency: str
    dry_run: bool


def load_config() -> Config:
    """Load config from environment variables.

    Secrets (API keys) are NOT loaded here yet; they will be loaded only when live trading is enabled.
    """

    db_path = os.getenv("TRADINGLAB_DB_PATH", os.path.join(os.getcwd(), "tradinglab.sqlite"))
    default_exchange = os.getenv("TRADINGLAB_EXCHANGE", "binance")
    base_currency = os.getenv("TRADINGLAB_BASE", "USDT")
    dry_run = os.getenv("TRADINGLAB_DRY_RUN", "1") not in ("0", "false", "False")

    return Config(
        db_path=db_path,
        default_exchange=default_exchange,
        base_currency=base_currency,
        dry_run=dry_run,
    )
