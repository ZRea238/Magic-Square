from rules.rules import MIN_VALUE

from .types import Grid
from .utils import diag_indexes, min_max_sum_from_values


def select_next_cell_with_candidates(
    target: int,
    size: int,
    row_sums: list[int],
    col_sums: list[int],
    row_unknowns: list[int],
    col_unknowns: list[int],
    diag_sums: list[int],
    diag_unknowns: list[int],
    used_values: set[int],
    max_cell_value: int,
    unknown_positions: list[tuple[int, int]],
    grid: Grid,
) -> tuple[int, int, list[int]] | None:
    best_choice: tuple[int, int, list[int]] | None = None
    best_domain_size: int | None = None

    for r, c in unknown_positions:
        if grid[r][c] is not None:
            continue

        candidates = valid_candidates_for_cell(
            target,
            size,
            r,
            c,
            row_sums,
            col_sums,
            row_unknowns,
            col_unknowns,
            diag_sums,
            diag_unknowns,
            used_values,
            max_cell_value,
        )
        if not candidates:
            return r, c, []

        domain_size = len(candidates)
        if best_domain_size is None or domain_size < best_domain_size:
            best_domain_size = domain_size
            best_choice = (r, c, candidates)

    return best_choice


def valid_candidates_for_cell(
    target: int,
    size: int,
    r: int,
    c: int,
    row_sums: list[int],
    col_sums: list[int],
    row_unknowns: list[int],
    col_unknowns: list[int],
    diag_sums: list[int],
    diag_unknowns: list[int],
    used_values: set[int],
    max_cell_value: int,
) -> list[int]:
    low, high = value_bounds_for_cell(
        target,
        size,
        r,
        c,
        row_sums,
        col_sums,
        row_unknowns,
        col_unknowns,
        diag_sums,
        diag_unknowns,
    )
    if low > high:
        return []
    high = min(high, max_cell_value)

    candidates: list[int] = []
    for value in range(low, high + 1):
        if can_place_value(
            value,
            r,
            c,
            target,
            size,
            row_sums,
            col_sums,
            row_unknowns,
            col_unknowns,
            diag_sums,
            diag_unknowns,
            used_values,
            max_cell_value,
        ):
            candidates.append(value)

    return candidates


def value_bounds_for_cell(
    target: int,
    size: int,
    r: int,
    c: int,
    row_sums: list[int],
    col_sums: list[int],
    row_unknowns: list[int],
    col_unknowns: list[int],
    diag_sums: list[int],
    diag_unknowns: list[int],
) -> tuple[int, int]:
    row_left = target - row_sums[r]
    col_left = target - col_sums[c]
    exact_values: list[int] = []
    upper_bound_candidates: list[int] = []

    if row_unknowns[r] == 1:
        exact_values.append(row_left)
    else:
        upper_bound_candidates.append(row_left - ((row_unknowns[r] - 1) * MIN_VALUE))

    if col_unknowns[c] == 1:
        exact_values.append(col_left)
    else:
        upper_bound_candidates.append(col_left - ((col_unknowns[c] - 1) * MIN_VALUE))

    for diag_index in diag_indexes(r, c, size):
        diag_left = target - diag_sums[diag_index]
        diag_unknown_count = diag_unknowns[diag_index]
        if diag_unknown_count == 1:
            exact_values.append(diag_left)
        else:
            upper_bound_candidates.append(diag_left - ((diag_unknown_count - 1) * MIN_VALUE))

    if exact_values:
        if any(value < MIN_VALUE for value in exact_values):
            return 1, 0
        if any(value != exact_values[0] for value in exact_values):
            return 1, 0

        exact = exact_values[0]
        if upper_bound_candidates and exact > min(upper_bound_candidates):
            return 1, 0
        return exact, exact

    if not upper_bound_candidates:
        return 1, 0

    return MIN_VALUE, min(upper_bound_candidates)


def can_place_value(
    value: int,
    r: int,
    c: int,
    target: int,
    size: int,
    row_sums: list[int],
    col_sums: list[int],
    row_unknowns: list[int],
    col_unknowns: list[int],
    diag_sums: list[int],
    diag_unknowns: list[int],
    used_values: set[int],
    max_cell_value: int,
) -> bool:
    if value in used_values:
        return False

    row_remaining_unknowns = row_unknowns[r] - 1
    col_remaining_unknowns = col_unknowns[c] - 1

    row_after = row_sums[r] + value
    col_after = col_sums[c] + value

    row_remaining_sum = target - row_after
    col_remaining_sum = target - col_after

    if row_remaining_unknowns == 0 and row_remaining_sum != 0:
        return False
    if col_remaining_unknowns == 0 and col_remaining_sum != 0:
        return False

    remaining_available = [
        candidate for candidate in range(MIN_VALUE, max_cell_value + 1) if candidate not in used_values and candidate != value
    ]

    if row_remaining_unknowns > 0:
        row_min_sum, row_max_sum = min_max_sum_from_values(remaining_available, row_remaining_unknowns)
        if row_remaining_sum < row_min_sum or row_remaining_sum > row_max_sum:
            return False

    if col_remaining_unknowns > 0:
        col_min_sum, col_max_sum = min_max_sum_from_values(remaining_available, col_remaining_unknowns)
        if col_remaining_sum < col_min_sum or col_remaining_sum > col_max_sum:
            return False

    for diag_index in diag_indexes(r, c, size):
        diag_remaining_unknowns = diag_unknowns[diag_index] - 1
        diag_after = diag_sums[diag_index] + value
        diag_remaining_sum = target - diag_after

        if diag_remaining_unknowns == 0 and diag_remaining_sum != 0:
            return False
        if diag_remaining_unknowns > 0:
            diag_min_sum, diag_max_sum = min_max_sum_from_values(remaining_available, diag_remaining_unknowns)
            if diag_remaining_sum < diag_min_sum or diag_remaining_sum > diag_max_sum:
                return False

    return True
