from typing import Optional
from rules.rules import MIN_VALUE


Grid = list[list[Optional[int]]]
SolvedGrid = list[list[int]]
TraceLog = list[str]


def solve_square(
    target: int,
    size: int,
    known_grid: Optional[Grid] = None,
    trace: bool = False,
    trace_log: Optional[TraceLog] = None,
) -> SolvedGrid:
    if size < 2:
        raise ValueError("size must be at least 2")
    if target <= size:
        raise ValueError("target must be greater than size")

    grid = _validate_and_normalize_known_grid(size=size, known_grid=known_grid)

    row_sums = [0] * size
    col_sums = [0] * size
    row_unknowns = [0] * size
    col_unknowns = [0] * size
    diag_sums = [0, 0]
    diag_unknowns = [0, 0]
    unknown_positions: list[tuple[int, int]] = []

    for r in range(size):
        for c in range(size):
            value = grid[r][c]
            if value is None:
                row_unknowns[r] += 1
                col_unknowns[c] += 1
                for diag_index in _diag_indexes(r, c, size):
                    diag_unknowns[diag_index] += 1
                unknown_positions.append((r, c))
            else:
                row_sums[r] += value
                col_sums[c] += value
                for diag_index in _diag_indexes(r, c, size):
                    diag_sums[diag_index] += value

    _validate_partial_sums(target, size, row_sums, row_unknowns, "row")
    _validate_partial_sums(target, size, col_sums, col_unknowns, "column")
    _validate_diagonal_partial_sums(target, diag_sums, diag_unknowns)
    _trace(
        trace,
        trace_log,
        f"Initialized search: size={size}, target={target}, unknown_cells={len(unknown_positions)}",
    )

    if not _search_solution(
        grid=grid,
        target=target,
        size=size,
        row_sums=row_sums,
        col_sums=col_sums,
        row_unknowns=row_unknowns,
        col_unknowns=col_unknowns,
        diag_sums=diag_sums,
        diag_unknowns=diag_unknowns,
        unknown_positions=unknown_positions,
        trace=trace,
        trace_log=trace_log,
        depth=0,
    ):
        raise ValueError("No valid solution for the provided target and known grid")

    return [[value for value in row if value is not None] for row in grid]


def _validate_and_normalize_known_grid(size: int, known_grid: Optional[Grid]) -> Grid:
    if known_grid is None:
        return [[None for _ in range(size)] for _ in range(size)]

    if not isinstance(known_grid, list) or len(known_grid) != size:
        raise ValueError("known_grid must be a square list with length equal to size")

    normalized_grid: Grid = []
    for row in known_grid:
        if not isinstance(row, list) or len(row) != size:
            raise ValueError("known_grid must be a square list with length equal to size")

        normalized_row: list[Optional[int]] = []
        for value in row:
            if value is None:
                normalized_row.append(None)
                continue
            if not isinstance(value, int):
                raise ValueError("known_grid entries must be integers or None")
            if value < MIN_VALUE:
                raise ValueError(f"known_grid integers must be at least {MIN_VALUE}")
            normalized_row.append(value)

        normalized_grid.append(normalized_row)

    return normalized_grid


def _validate_partial_sums(
    target: int,
    size: int,
    sums: list[int],
    unknown_counts: list[int],
    axis_name: str,
) -> None:
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


def _validate_diagonal_partial_sums(target: int, diag_sums: list[int], diag_unknowns: list[int]) -> None:
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


def _search_solution(
    grid: Grid,
    target: int,
    size: int,
    row_sums: list[int],
    col_sums: list[int],
    row_unknowns: list[int],
    col_unknowns: list[int],
    diag_sums: list[int],
    diag_unknowns: list[int],
    unknown_positions: list[tuple[int, int]],
    trace: bool,
    trace_log: Optional[TraceLog],
    depth: int,
) -> bool:
    choice = _select_next_cell(
        target,
        size,
        row_sums,
        col_sums,
        row_unknowns,
        col_unknowns,
        diag_sums,
        diag_unknowns,
        unknown_positions,
        grid,
    )
    if choice is None:
        _trace(trace, trace_log, f"{_indent(depth)}All cells assigned; validating final sums")
        return (
            all(row_sums[i] == target for i in range(size))
            and all(col_sums[i] == target for i in range(size))
            and diag_sums[0] == target
            and diag_sums[1] == target
        )

    r, c, low, high = choice
    _trace(trace, trace_log, f"{_indent(depth)}Select cell ({r}, {c}) with domain [{low}, {high}]")
    for value in range(low, high + 1):
        if not _can_place_value(
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
        ):
            _trace(trace, trace_log, f"{_indent(depth)}Prune value {value} at ({r}, {c})")
            continue

        _trace(trace, trace_log, f"{_indent(depth)}Try value {value} at ({r}, {c})")
        grid[r][c] = value
        row_sums[r] += value
        col_sums[c] += value
        row_unknowns[r] -= 1
        col_unknowns[c] -= 1
        for diag_index in _diag_indexes(r, c, size):
            diag_sums[diag_index] += value
            diag_unknowns[diag_index] -= 1

        if _search_solution(
            grid=grid,
            target=target,
            size=size,
            row_sums=row_sums,
            col_sums=col_sums,
            row_unknowns=row_unknowns,
            col_unknowns=col_unknowns,
            diag_sums=diag_sums,
            diag_unknowns=diag_unknowns,
            unknown_positions=unknown_positions,
            trace=trace,
            trace_log=trace_log,
            depth=depth + 1,
        ):
            _trace(trace, trace_log, f"{_indent(depth)}Accept value {value} at ({r}, {c})")
            return True

        _trace(trace, trace_log, f"{_indent(depth)}Backtrack on ({r}, {c}) value {value}")
        grid[r][c] = None
        row_sums[r] -= value
        col_sums[c] -= value
        row_unknowns[r] += 1
        col_unknowns[c] += 1
        for diag_index in _diag_indexes(r, c, size):
            diag_sums[diag_index] -= value
            diag_unknowns[diag_index] += 1

    _trace(trace, trace_log, f"{_indent(depth)}No valid values remain for ({r}, {c})")
    return False


def _select_next_cell(
    target: int,
    size: int,
    row_sums: list[int],
    col_sums: list[int],
    row_unknowns: list[int],
    col_unknowns: list[int],
    diag_sums: list[int],
    diag_unknowns: list[int],
    unknown_positions: list[tuple[int, int]],
    grid: Grid,
) -> Optional[tuple[int, int, int, int]]:
    best_choice: Optional[tuple[int, int, int, int]] = None
    best_domain_size: Optional[int] = None

    for r, c in unknown_positions:
        if grid[r][c] is not None:
            continue

        low, high = _value_bounds_for_cell(
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
            return (r, c, 1, 0)

        domain_size = high - low + 1
        if best_domain_size is None or domain_size < best_domain_size:
            best_domain_size = domain_size
            best_choice = (r, c, low, high)

    return best_choice


def _value_bounds_for_cell(
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

    for diag_index in _diag_indexes(r, c, size):
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


def _can_place_value(
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
) -> bool:
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
    if row_remaining_unknowns > 0 and row_remaining_sum < row_remaining_unknowns * MIN_VALUE:
        return False
    if col_remaining_unknowns > 0 and col_remaining_sum < col_remaining_unknowns * MIN_VALUE:
        return False

    for diag_index in _diag_indexes(r, c, size):
        diag_remaining_unknowns = diag_unknowns[diag_index] - 1
        diag_after = diag_sums[diag_index] + value
        diag_remaining_sum = target - diag_after

        if diag_remaining_unknowns == 0 and diag_remaining_sum != 0:
            return False
        if diag_remaining_unknowns > 0 and diag_remaining_sum < diag_remaining_unknowns * MIN_VALUE:
            return False

    return True


def _diag_indexes(r: int, c: int, size: int) -> list[int]:
    indexes: list[int] = []
    if r == c:
        indexes.append(0)
    if r + c == size - 1:
        indexes.append(1)
    return indexes


def _trace(enabled: bool, trace_log: Optional[TraceLog], message: str) -> None:
    if not enabled:
        return
    if trace_log is not None:
        trace_log.append(message)
    else:
        print(message)


def _indent(depth: int) -> str:
    return "  " * depth
