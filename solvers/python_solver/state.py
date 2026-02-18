from typing import Optional

from rules.rules import MIN_VALUE

from .types import GameMode, Grid
from .utils import diag_indexes
from .validation import (
    resolve_max_cell_value,
    validate_and_normalize_known_grid,
    validate_diagonal_partial_sums,
    validate_partial_sums,
)


InitialState = tuple[
    Grid,
    list[int],
    list[int],
    list[int],
    list[int],
    list[int],
    list[int],
    set[int],
    list[tuple[int, int]],
]


def build_initial_state(target: int, size: int, known_grid: Optional[Grid], game_mode: GameMode) -> InitialState:
    if size < 2:
        raise ValueError("size must be at least 2")
    if target <= size:
        raise ValueError("target must be greater than size")

    max_cell_value = resolve_max_cell_value(target=target, size=size, game_mode=game_mode)
    if max_cell_value < MIN_VALUE:
        raise ValueError("No valid value range is available for this game mode and target")

    grid = validate_and_normalize_known_grid(size=size, known_grid=known_grid, max_cell_value=max_cell_value)

    row_sums = [0] * size
    col_sums = [0] * size
    row_unknowns = [0] * size
    col_unknowns = [0] * size
    diag_sums = [0, 0]
    diag_unknowns = [0, 0]
    used_values: set[int] = set()
    unknown_positions: list[tuple[int, int]] = []

    for r in range(size):
        for c in range(size):
            value = grid[r][c]
            if value is None:
                row_unknowns[r] += 1
                col_unknowns[c] += 1
                for diag_index in diag_indexes(r, c, size):
                    diag_unknowns[diag_index] += 1
                unknown_positions.append((r, c))
            else:
                if value in used_values:
                    raise ValueError("known_grid cannot contain duplicate values")
                used_values.add(value)
                row_sums[r] += value
                col_sums[c] += value
                for diag_index in diag_indexes(r, c, size):
                    diag_sums[diag_index] += value

    validate_partial_sums(target, size, row_sums, row_unknowns, "row")
    validate_partial_sums(target, size, col_sums, col_unknowns, "column")
    validate_diagonal_partial_sums(target, diag_sums, diag_unknowns)

    return (
        grid,
        row_sums,
        col_sums,
        row_unknowns,
        col_unknowns,
        diag_sums,
        diag_unknowns,
        used_values,
        unknown_positions,
    )


def apply_value(
    value: int,
    r: int,
    c: int,
    size: int,
    grid: Grid,
    row_sums: list[int],
    col_sums: list[int],
    row_unknowns: list[int],
    col_unknowns: list[int],
    diag_sums: list[int],
    diag_unknowns: list[int],
    used_values: set[int],
) -> None:
    grid[r][c] = value
    row_sums[r] += value
    col_sums[c] += value
    row_unknowns[r] -= 1
    col_unknowns[c] -= 1
    for diag_index in diag_indexes(r, c, size):
        diag_sums[diag_index] += value
        diag_unknowns[diag_index] -= 1
    used_values.add(value)


def revert_value(
    value: int,
    r: int,
    c: int,
    size: int,
    grid: Grid,
    row_sums: list[int],
    col_sums: list[int],
    row_unknowns: list[int],
    col_unknowns: list[int],
    diag_sums: list[int],
    diag_unknowns: list[int],
    used_values: set[int],
) -> None:
    grid[r][c] = None
    row_sums[r] -= value
    col_sums[c] -= value
    row_unknowns[r] += 1
    col_unknowns[c] += 1
    for diag_index in diag_indexes(r, c, size):
        diag_sums[diag_index] -= value
        diag_unknowns[diag_index] += 1
    used_values.remove(value)


def final_constraints_met(target: int, size: int, row_sums: list[int], col_sums: list[int], diag_sums: list[int]) -> bool:
    return (
        all(row_sums[i] == target for i in range(size))
        and all(col_sums[i] == target for i in range(size))
        and diag_sums[0] == target
        and diag_sums[1] == target
    )
