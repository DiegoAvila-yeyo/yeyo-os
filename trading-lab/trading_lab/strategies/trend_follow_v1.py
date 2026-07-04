from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True)
class Signal:
    side: str  # 'long' or 'none'
    rationale: str


def compute_signal(ohlcv: list[list[float]]) -> Signal:
    """Very simple, conservative trend filter.

    This is intentionally minimal and NOT a promise of profitability.
    We only decide whether the market is in an uptrend (long-only) or we stay in cash.

    ohlcv rows: [timestamp_ms, open, high, low, close, volume]
    """

    if len(ohlcv) < 210:
        return Signal(side="none", rationale="Not enough history (need ~210 daily candles)")

    df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
    df["sma50"] = df["close"].rolling(50).mean()
    df["sma200"] = df["close"].rolling(200).mean()

    last = df.iloc[-1]
    if pd.isna(last["sma50"]) or pd.isna(last["sma200"]):
        return Signal(side="none", rationale="SMA not ready")

    uptrend = (last["close"] > last["sma200"]) and (last["sma50"] > last["sma200"])
    if uptrend:
        return Signal(side="long", rationale="Uptrend filter: close>sma200 and sma50>sma200")

    return Signal(side="none", rationale="No uptrend: stay in USDT")
