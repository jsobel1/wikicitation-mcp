"""
progress.py
Lightweight progress reporting for paginated / batch operations.

Emits structured INFO-level log lines at controlled cadence:
  - For known totals: percentage milestones (every 5%, plus start/end).
  - For unknown totals (open-ended pagination): every Nth item.

Why log lines instead of a progress-bar dependency: this module is consumed
both directly from Python (where INFO logs surface in any normal logging
setup) and via the MCP server (where stderr is the user-visible channel,
and FastMCP forwards stderr-as-events). No tqdm dependency, no flicker, no
TTY-detection logic — just well-formed log records the caller can route.

Usage
-----
    with Progress("fetch revisions", total=expected) as p:
        for batch in pages:
            p.update(len(batch))

If `total` is None, Progress falls back to "open-ended" mode and emits every
`tick_every` items instead of percentages.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger("wikicitation.progress")


class Progress:
    """
    Context-managed progress reporter.

    Parameters
    ----------
    label : str
        Short tag identifying the operation, e.g. "fetch revisions: Zeitgeber".
    total : int | None
        Expected final count, if known. None ⇒ open-ended mode.
    step_pct : float
        Minimum percentage advance before re-emitting a milestone (default 5).
    tick_every : int
        In open-ended mode, emit every Nth item (default 100).
    min_interval_s : float
        Floor on time between emissions, regardless of advance (default 1.0)
        — keeps logs sparse on very fast batches.
    """

    def __init__(
        self,
        label: str,
        total: Optional[int] = None,
        *,
        step_pct: float = 5.0,
        tick_every: int = 100,
        min_interval_s: float = 1.0,
    ) -> None:
        self.label = label
        self.total = total
        self.step_pct = step_pct
        self.tick_every = max(1, tick_every)
        self.min_interval_s = min_interval_s

        self.count = 0
        self._last_emit_pct = -step_pct
        self._last_emit_count = 0
        self._last_emit_ts = 0.0
        self._started_ts = 0.0

    # ------------------------------------------------------------------
    def __enter__(self) -> "Progress":
        self._started_ts = time.monotonic()
        if self.total:
            logger.info("%s: starting (target %d)", self.label, self.total)
        else:
            logger.info("%s: starting", self.label)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        elapsed = time.monotonic() - self._started_ts
        if exc is None:
            logger.info(
                "%s: done — %d items in %.1fs (%.1f items/s)",
                self.label, self.count, elapsed,
                self.count / elapsed if elapsed > 0 else 0.0,
            )
        else:
            logger.warning(
                "%s: aborted after %d items / %.1fs (%s)",
                self.label, self.count, elapsed, exc_type.__name__,
            )

    # ------------------------------------------------------------------
    def update(self, increment: int = 1) -> None:
        """Advance the counter by `increment` and emit a milestone if appropriate."""
        if increment <= 0:
            return
        self.count += increment

        now = time.monotonic()
        if now - self._last_emit_ts < self.min_interval_s:
            return

        if self.total:
            pct = 100.0 * self.count / self.total
            if pct - self._last_emit_pct >= self.step_pct or self.count >= self.total:
                logger.info(
                    "%s: %.0f%% (%d/%d)",
                    self.label, pct, self.count, self.total,
                )
                self._last_emit_pct = pct
                self._last_emit_ts = now
        else:
            if self.count - self._last_emit_count >= self.tick_every:
                logger.info("%s: %d items so far", self.label, self.count)
                self._last_emit_count = self.count
                self._last_emit_ts = now
