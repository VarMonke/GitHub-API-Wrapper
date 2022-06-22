from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import timedelta

__all__ = ("human_readable_time_until",)


def human_readable_time_until(td: timedelta) -> str:
    seconds = int(td.total_seconds())
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    return f"{hours} hours, {minutes} minues, {seconds} seconds"
