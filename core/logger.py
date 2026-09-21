"""Logging utilities."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

LOG_DIR   = Path(os.getenv("LOGS_DIR", "logs"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()


class EnvRedactionFilter(logging.Filter):
    """
    Scrub secrets from all log messages.

    Rule: redact any env var VALUE (≥8 chars) whose name contains:
    KEY, TOKEN, SECRET, PASSWORD
    """

    _needles: tuple[str, ...] = ("KEY", "TOKEN", "SECRET", "PASSWORD")
    _REDACTED = "[REDACTED]"

    def __init__(self) -> None:
        super().__init__()
        self._patterns: list[re.Pattern[str]] = self._build_patterns()

    def _build_patterns(self) -> list[re.Pattern[str]]:
        patterns: list[re.Pattern[str]] = []
        for key, val in os.environ.items():
            if any(needle in key.upper() for needle in self._needles):
                if val and len(val) >= 8:
                    patterns.append(re.compile(re.escape(val)))
        return patterns

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        for pat in self._patterns:
            msg = pat.sub(self._REDACTED, msg)
        record.msg  = msg
        record.args = None
        return True


def _build_logger(name: str = "diana") -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    redact = EnvRedactionFilter()

    # File handler — rotates daily via a simple fixed path
    fh = logging.FileHandler(LOG_DIR / "diana.log", encoding="utf-8")
    fh.setFormatter(fmt)
    fh.addFilter(redact)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch.addFilter(redact)
    logger.addHandler(ch)

    return logger


def get_logger(name: str = "diana") -> logging.Logger:
    """Return a configured logger with secret redaction enabled."""
    return _build_logger(name)


# Module-level default logger
log = get_logger()
