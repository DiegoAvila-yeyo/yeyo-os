"""
YeyoNet — Satellite Configuration.
Persists satellite credentials to ~/.yeyonet/satellite.json
so the WebSocket client can auto-connect on startup.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger("yeyonet.satellite_config")

CONFIG_DIR = Path.home() / ".yeyonet"
CONFIG_FILE = CONFIG_DIR / "satellite.json"


class SatelliteConfig(TypedDict):
    node_id: str
    auth_token: str
    central_ws_url: str
    central_name: str
    connected_at: str


def save_config(
    node_id: str,
    auth_token: str,
    central_ws_url: str,
    central_name: str = "",
) -> SatelliteConfig:
    """Save satellite credentials to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config: SatelliteConfig = {
        "node_id": node_id,
        "auth_token": auth_token,
        "central_ws_url": central_ws_url,
        "central_name": central_name,
        "connected_at": datetime.now(timezone.utc).isoformat(),
    }
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")
    logger.info(f"[satellite_config] Saved config to {CONFIG_FILE}")
    return config


def load_config() -> SatelliteConfig | None:
    """Load satellite credentials from disk. Returns None if not configured."""
    if not CONFIG_FILE.exists():
        return None
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        # Validate required keys
        for key in ("node_id", "auth_token", "central_ws_url"):
            if key not in data:
                logger.warning(f"[satellite_config] Missing key '{key}' in config")
                return None
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"[satellite_config] Failed to load config: {e}")
        return None


def clear_config() -> bool:
    """Remove satellite config file."""
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
        logger.info("[satellite_config] Config cleared")
        return True
    return False


def is_configured() -> bool:
    """Check if a satellite config exists."""
    return load_config() is not None
