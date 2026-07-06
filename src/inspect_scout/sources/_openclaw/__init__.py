"""OpenClaw import sources.

Hosts the family of OpenClaw importers: ``_sessions`` (native session bundles
under ``~/.openclaw/`` — the canonical format, entry point ``openclaw``) and
``_telemetry_hal`` (JSONL telemetry written by the ``openclaw-telemetry-hal``
plugin). Both set ``agent="openclaw"`` and coexist in one database,
distinguished by ``source_type``.
"""

from ._sessions import OPENCLAW_SOURCE_TYPE, openclaw
from ._telemetry_hal import (
    OPENCLAW_TELEMETRY_HAL_SOURCE_TYPE,
    openclaw_telemetry_hal,
)

__all__ = [
    "openclaw",
    "OPENCLAW_SOURCE_TYPE",
    "openclaw_telemetry_hal",
    "OPENCLAW_TELEMETRY_HAL_SOURCE_TYPE",
]
