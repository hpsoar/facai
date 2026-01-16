"""Proxy resolution helpers."""

from __future__ import annotations

import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

DEFAULT_PROXY_URL = "http://127.0.0.1:7897"


def resolve_proxy(explicit: Optional[str] = None) -> Optional[str]:
    """Return the effective proxy URL, falling back to a sane default.

    Precedence:
    1. Explicit argument if provided.
    2. Environment variable ``YF_PROXY``.
    3. The default local proxy ``http://127.0.0.1:7897``.

    Empty strings disable proxy usage.
    """

    candidate = explicit if explicit is not None else os.environ.get("YF_PROXY")
    if candidate is None:
        candidate = DEFAULT_PROXY_URL
    logger.info("proxy=%s", candidate)
    candidate = candidate.strip() if candidate else ""
    return candidate or None
