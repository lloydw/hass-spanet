"""Bounded API-confirmed readback after a SpaNET pump-mode command.

This is separate from the normal five-minute poll. It does not assume
a successful PUT means the motor has already changed mode.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

# First verification GET 5s after the PUT completes, retry 15s later.
PUMP_READBACK_DELAYS_SECONDS = (5, 15)


async def readback_until_confirmed(
    expected_mode: str,
    get_reported_mode: Callable[[], str | None],
    refresh: Callable[[], Awaitable[Any]],
    *,
    delays: Sequence[float] = PUMP_READBACK_DELAYS_SECONDS,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> bool:
    """Poll at most twice, returning True only for API-reported matches.

    A failed readback is not a failed pump command: the regular poll
    remains active. Cancellation intentionally propagates so a newer
    command or integration unload can stop a pending readback.
    """
    for delay in delays:
        await sleep(delay)
        try:
            await refresh()
            reported_mode = get_reported_mode()
        except Exception:
            # Transient failures, including SpaNET API 202s, get only one
            # extra confirmation attempt, not an unbounded retry loop.
            continue
        if reported_mode == expected_mode:
            return True
    return False
