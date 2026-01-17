"""Proxy resolution helpers."""

from __future__ import annotations

import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def resolve_proxy(explicit: Optional[str] = None) -> Optional[str]:
    """Return the effective proxy URL, preferring explicit settings over env vars."""

    candidate = explicit if explicit is not None else os.environ.get("YF_PROXY")
    candidate = candidate.strip() if candidate else ""
    logger.info("proxy=%s", candidate or "disabled")
    return candidate or None
