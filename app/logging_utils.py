"""Central logging configuration for the portfolio MCP server."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

DEFAULT_LOG_FILE = "/tmp/logs/facai-mcp.log"
DEFAULT_LOG_LEVEL = "INFO"


def setup_logging(log_file: Optional[str] = None, level_name: Optional[str] = None) -> Path:
    """Configure application-wide logging directed to a file.

    Parameters can be supplied directly or via environment variables:
    - ``PORTFOLIO_LOG_FILE``: file path for log output (defaults to logs/facai-mcp.log).
    - ``PORTFOLIO_LOG_LEVEL``: logging level (DEBUG, INFO, WARNING, etc.).

    Returns the resolved log file path so callers can report it.
    """

    resolved_path = Path(
        (log_file or os.environ.get("PORTFOLIO_LOG_FILE") or DEFAULT_LOG_FILE)
    ).expanduser()
    level_str = (level_name or os.environ.get("PORTFOLIO_LOG_LEVEL") or DEFAULT_LOG_LEVEL).upper()
    level = getattr(logging, level_str, logging.INFO)

    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(resolved_path, encoding="utf-8")

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[handler],
        force=True,
    )

    logging.getLogger("yfinance").setLevel(logging.WARNING)
    logging.getLogger("yfinance.data").setLevel(logging.WARNING)
    logging.getLogger("yfinance.utils").setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging initialized level=%s path=%s", level_str, resolved_path
    )

    return resolved_path
