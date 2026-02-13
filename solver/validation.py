from typing import Optional

from rules.rules import MIN_VALUE

from .types import GameMode, Grid
from .utils import min_max_sum_from_values


def resolve_max_cell_value(target: int, size: int, game_mode: GameMode) -> int:
    if game_mode == "unbounded":
        return target - 1
    if game_mode == "bounded_by_size_squared":
        return min(target - 1, size * size)
    raise ValueError("game_mode must be one of: unbounded, bounded_by_size_squared")


def validate_and_normalize_known_grid(size: int, known_grid: Optional[Grid], max_cell_value: int) -> Grid:
    if known_grid is None:
        return [[None for _ in range(size)] for _ in range(size)]

    if not isinstance(known_grid, list) or len(known_grid) != size:
        raise ValueError("known_grid must be a square list with length equal to size")

    normalized_grid: Grid = []
    for row in known_grid:
        if not isinstance(row, list) or len(row) != size:
            raise ValueError("known_grid must be a square list with length equal to size")

        normalized_row = []
        for value in row:
            if value is None:
                normalized_row.append(None)
                continue
            if not isinstance(value, int):
                raise ValueError("known_grid entries must be integers or None")
            if value < MIN_VALUE:
                raise ValueError(f"known_grid integers must be at least {MIN_VALUE}")
            if value > max_cell_value:
                raise ValueError(f"known_grid integers must be at most {max_cell_value} for the selected game mode")
            normalized_row.append(value)

        normalized_grid.append(normalized_row)

    return normalized_grid


def validate_partial_sums(target: int, size: int, sums: list[int], unknown_counts: list[int], axis_name: str) -> None:
    for index in range(size):
        current_sum = sums[index]
        unknowns = unknown_counts[index]

        if unknowns == 0 and current_sum != target:
            raise ValueError(f"known {axis_name} {index} does not sum to target")
        if unknowns > 0 and current_sum >= target:
            raise ValueError(f"known values in {axis_name} {index} are too large to reach target")

        min_possible = current_sum + (unknowns * MIN_VALUE)
        if min_possible > target:
            raise ValueError(f"{axis_name} {index} cannot reach target with minimum value {MIN_VALUE}")


def validate_diagonal_partial_sums(target: int, diag_sums: list[int], diag_unknowns: list[int]) -> None:
    for diag_index, axis_name in enumerate(["main diagonal", "anti diagonal"]):
        current_sum = diag_sums[diag_index]
        unknowns = diag_unknowns[diag_index]

        if unknowns == 0 and current_sum != target:
            raise ValueError(f"known {axis_name} does not sum to target")
        if unknowns > 0 and current_sum >= target:
            raise ValueError(f"known values in {axis_name} are too large to reach target")

        min_possible = current_sum + (unknowns * MIN_VALUE)
        if min_possible > target:
            raise ValueError(f"{axis_name} cannot reach target with minimum value {MIN_VALUE}")


def validate_global_uniqueness_feasibility(
    target: int,
    size: int,
    grid: Grid,
    used_values: set[int],
    max_cell_value: int,
) -> None:
    required_total = size * target
    cell_count = size * size
    min_total_unique = cell_count * (cell_count + 1) // 2
    if required_total < min_total_unique:
        raise ValueError("target is too small to build a grid of unique positive integers")

    unknown_count = sum(1 for row in grid for value in row if value is None)
    known_total = sum(value for row in grid for value in row if value is not None)

    unused_values = [value for value in range(MIN_VALUE, max_cell_value + 1) if value not in used_values]
    if len(unused_values) < unknown_count:
        raise ValueError("Not enough unique values available below target to fill all unknown cells")

    min_unknown_sum, max_unknown_sum = min_max_sum_from_values(unused_values, unknown_count)
    required_unknown_sum = required_total - known_total
    if required_unknown_sum < min_unknown_sum or required_unknown_sum > max_unknown_sum:
        raise ValueError("known values make the unique-value total sum impossible for this target")


def validate_count_options(
    game_mode: GameMode,
    mode: str,
    max_seconds: Optional[float],
    sample_paths: int,
    progress_interval: int,
    workers: Optional[int],
) -> None:
    if game_mode not in {"unbounded", "bounded_by_size_squared"}:
        raise ValueError("game_mode must be one of: unbounded, bounded_by_size_squared")
    if mode not in {"auto", "exact", "estimate"}:
        raise ValueError("mode must be one of: auto, exact, estimate")
    if max_seconds is not None and max_seconds < 0:
        raise ValueError("max_seconds must be >= 0")
    if sample_paths < 1:
        raise ValueError("sample_paths must be >= 1")
    if progress_interval < 1:
        raise ValueError("progress_interval must be >= 1")
    if workers is not None and workers < 1:
        raise ValueError("workers must be >= 1")
