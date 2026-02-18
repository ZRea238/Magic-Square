from typing import Optional

from .types import TraceLog


def diag_indexes(r: int, c: int, size: int) -> list[int]:
    indexes: list[int] = []
    if r == c:
        indexes.append(0)
    if r + c == size - 1:
        indexes.append(1)
    return indexes


def trace(enabled: bool, trace_log: Optional[TraceLog], message: str) -> None:
    if not enabled:
        return
    if trace_log is not None:
        trace_log.append(message)
    else:
        print(message)


def indent(depth: int) -> str:
    return "  " * depth


def min_max_sum_from_values(values: list[int], count: int) -> tuple[int, int]:
    if count == 0:
        return 0, 0
    if len(values) < count:
        return 1, 0
    sorted_values = sorted(values)
    min_sum = sum(sorted_values[:count])
    max_sum = sum(sorted_values[-count:])
    return min_sum, max_sum
