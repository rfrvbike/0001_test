"""Fail-closed live mode gate for future X API reads."""

from __future__ import annotations

from typing import Any, Mapping


def assert_live_mode_allowed(config: Mapping[str, Any] | None = None) -> None:
    """Allow dry-run paths and reject every live-mode attempt.

    Live X API access is intentionally disabled at this stage, even when a
    credential-shaped bundle is available.
    """

    values = dict(config or {})
    dry_run = values.get("dry_run", True)
    live_mode = values.get("live_mode", False)
    if dry_run and not live_mode:
        return
    raise RuntimeError("live mode disabled")
