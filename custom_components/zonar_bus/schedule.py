"""When the school bus runs, so Zonar is only polled during a run."""

from __future__ import annotations

from datetime import datetime, time

_MORNING = (time(6, 30), time(8, 45))
_MORNING_WED = (time(6, 30), time(9, 45))  # Wednesday runs an hour later
_AFTERNOON = (time(15, 15), time(18, 30))

# Local-time windows per weekday (Monday = 0). Weekends have none.
RUN_WINDOWS: dict[int, list[tuple[time, time]]] = {
    0: [_MORNING, _AFTERNOON],
    1: [_MORNING, _AFTERNOON],
    2: [_MORNING_WED, _AFTERNOON],
    3: [_MORNING, _AFTERNOON],
    4: [_MORNING, _AFTERNOON],
}


def in_run_window(now: datetime) -> bool:
    """Whether a local datetime falls inside one of the bus run windows."""
    return any(start <= now.time() < end for start, end in RUN_WINDOWS.get(now.weekday(), []))
