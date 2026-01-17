"""Environment-driven configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the MCP server."""

    portfolio_file: Path
    refresh_interval_seconds: int
    price_ttl_seconds: int


def _parse_int_env(var: str, default: int) -> int:
    raw = os.environ.get(var)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {var} must be an integer, got {raw!r}") from exc
    return max(0, value)


def load_settings() -> Settings:
    """Build settings from environment variables with sane defaults."""

    portfolio_file = Path(os.environ.get("PORTFOLIO_FILE", "data/portfolio.yaml")).expanduser()
    refresh_interval = _parse_int_env("REFRESH_INTERVAL_SECONDS", 900)
    price_ttl = _parse_int_env("PRICE_TTL_SECONDS", 300)
    return Settings(
        portfolio_file=portfolio_file,
        refresh_interval_seconds=refresh_interval,
        price_ttl_seconds=price_ttl,
    )
