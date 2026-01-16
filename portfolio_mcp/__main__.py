"""Entry point for running the portfolio MCP server."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .app import PortfolioApp
from .config import load_settings
from .logging_utils import setup_logging
from .server import build_server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Facai Portfolio MCP Server")
    parser.add_argument(
        "--transport",
        default="stdio",
        help="MCP transport to use (stdio, http, streamable-http, etc.)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP transports")
    parser.add_argument("--port", default=8000, type=int, help="Port for HTTP transports")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()
    settings.portfolio_file.parent.mkdir(parents=True, exist_ok=True)

    log_path = setup_logging()
    logging.getLogger(__name__).info(
        "Starting portfolio MCP transport=%s host=%s port=%s log=%s",
        args.transport,
        getattr(args, "host", None),
        getattr(args, "port", None),
        log_path,
    )

    app = PortfolioApp(settings)
    server = build_server(app, name="Facai Portfolio MCP", version=__version__)

    run_kwargs = {"transport": args.transport}
    if args.transport in {"http", "streamable-http", "sse"}:
        run_kwargs["host"] = args.host
        run_kwargs["port"] = args.port

    try:
        server.run(**run_kwargs)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
