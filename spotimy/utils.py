"""
Various utility functions.
"""

from typing import Sequence, TypeVar

T = TypeVar("T")


def percentile(lst: Sequence[T], pct: float) -> T:
    """
    Return item at pct% position in lst.
    """
    return lst[int(len(lst) * pct)]


def ms_to_human(duration_ms: int) -> str:
    """
    Convert a duration in ms to a human readable string.
    """
    minutes = int(duration_ms / 60000)
    remain = duration_ms - minutes * 60000
    seconds = int(remain / 1000)
    return f"{minutes}:{seconds}"
