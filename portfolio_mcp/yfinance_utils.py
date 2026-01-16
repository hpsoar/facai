"""Helpers for configuring yfinance network behavior."""

from __future__ import annotations

import logging
import os
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)


def configure_network(proxy: Optional[str], retries: Optional[int] = None) -> None:
    """Update yfinance global network settings for proxy/retry behavior."""

    # Explicitly disable proxy by clearing environment variables
    # This prevents curl_cffi from reading system proxy settings
    if proxy is None or proxy == "":
        for var in [
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "http_proxy",
            "https_proxy",
            "ALL_PROXY",
            "all_proxy",
        ]:
            if var in os.environ:
                del os.environ[var]
                logger.debug(f"Cleared proxy environment variable: {var}")
    else:
        # If proxy is provided, set environment variables for curl_cffi
        os.environ["HTTP_PROXY"] = proxy
        os.environ["HTTPS_PROXY"] = proxy
        logger.debug(f"Set proxy to: {proxy}")

    if retries is not None:
        normalized_retries = max(int(retries), 0)
        if normalized_retries != getattr(yf.config.network, "retries", None):
            yf.config.network.retries = normalized_retries
            logger.debug("yfinance retries set to %s", normalized_retries)
