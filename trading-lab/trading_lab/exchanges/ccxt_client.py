from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import ccxt


@dataclass(frozen=True)
class ExchangeClient:
    name: str
    client: Any


def make_public_exchange(name: str) -> ExchangeClient:
    """Create a public (no keys) CCXT exchange client."""

    if not hasattr(ccxt, name):
        raise ValueError(f"Unknown/unsupported exchange in ccxt: {name}")

    klass = getattr(ccxt, name)
    client = klass({"enableRateLimit": True})
    return ExchangeClient(name=name, client=client)
