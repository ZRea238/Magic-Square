import math
import os
import random
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from typing import Callable, Optional

from rules.rules import MIN_VALUE


Grid = list[list[Optional[int]]]
SolvedGrid = list[list[int]]
TraceLog = list[str]
CountResult = dict[str, object]
ProgressState = dict[str, int]
GameMode = str


def _resolve_max_cell_value(target: int, size: int, game_mode: GameMode) -> int:
    if game_mode == "unbounded":
        return target - 1
    if game_mode == "bounded_by_size_squared":
        return min(target - 1, size * size)
    raise ValueError("game_mode must be one of: unbounded, bounded_by_size_squared")


def solve_square(
    target: int,
    size: int,
    known_grid: Optional[Grid] = None,
    game_mode: GameMode = "unbounded",
    trace: bool = False,
    trace_log: Optional[TraceLog] = None,
) -> SolvedGrid:
    (
        grid,
        row_sums,
        col_sums,
        row_unknowns,
        col_unknowns,
        diag_sums,
        diag_unknowns,
        used_values,
        unknown_positions,
    ) = _build_initial_state(target=target, size=size, known_grid=known_grid, game_mode=game_mode)
    max_cell_value = _resolve_max_cell_value(target=target, size=size, game_mode=game_mode)

    _trace(
        trace,
        trace_log,
        f"Initialized search: size={size}, target={target}, unknown_cells={len(unknown_positions)}",
    )

    if not _search_first_solution(
        grid=grid,
        target=target,
        size=size,
        row_sums=row_sums,
        col_sums=col_sums,
        row_unknowns=row_unknowns,
        col_unknowns=col_unknowns,
        diag_sums=diag_sums,
        diag_unknowns=diag_unknowns,
        used_values=used_values,
        max_cell_value=max_cell_value,
        unknown_positions=unknown_positions,
        trace=trace,
        trace_log=trace_log,
        depth=0,
    ):
        raise ValueError("No valid solution for the provided target and known grid")

    return [[value for value in row if value is not None] for row in grid]


def count_solutions(
    target: int,
    size: int,
    known_grid: Optional[Grid] = None,
    game_mode: GameMode = "unbounded",
    mode: str = "auto",
    max_seconds: Optional[float] = 2.0,
    sample_paths: int = 300,
    stop_requested: Optional[Callable[[], bool]] = None,
    progress_callback: Optional[Callable[[ProgressState], None]] = None,
    progress_interval: int = 200,
    use_multiprocessing: bool = False,
    workers: Optional[int] = None,
) -> CountResult:
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

    (
        grid,
        row_sums,
        col_sums,
        row_unknowns,
        col_unknowns,
        diag_sums,
        diag_unknowns,
        used_values,
        unknown_positions,
    ) = _build_initial_state(target=target, size=size, known_grid=known_grid, game_mode=game_mode)
    max_cell_value = _resolve_max_cell_value(target=target, size=size, game_mode=game_mode)
    _validate_global_uniqueness_feasibility(target, size, grid, used_values, max_cell_value)

    if mode in {"auto", "exact"}:
        deadline = None if max_seconds is None else time.monotonic() + max_seconds
        progress_state: ProgressState = {"solutions_found": 0, "nodes_visited": 0}
        if use_multiprocessing:
            exact_count, timed_out = _count_all_solutions_multiprocess(
                grid=grid,
                target=target,
                size=size,
                row_sums=row_sums,
                col_sums=col_sums,
                row_unknowns=row_unknowns,
                col_unknowns=col_unknowns,
                diag_sums=diag_sums,
                diag_unknowns=diag_unknowns,
                used_values=used_values,
                max_cell_value=max_cell_value,
                unknown_positions=unknown_positions,
                deadline=deadline,
                stop_requested=stop_requested,
                progress_callback=progress_callback,
                workers=workers,
                game_mode=game_mode,
            )
        else:
            exact_count, timed_out = _count_all_solutions(
                grid=grid,
                target=target,
                size=size,
                row_sums=row_sums,
                col_sums=col_sums,
                row_unknowns=row_unknowns,
                col_unknowns=col_unknowns,
                diag_sums=diag_sums,
                diag_unknowns=diag_unknowns,
                used_values=used_values,
                max_cell_value=max_cell_value,
                unknown_positions=unknown_positions,
                deadline=deadline,
                stop_requested=stop_requested,
                progress_callback=progress_callback,
                progress_interval=progress_interval,
                progress_state=progress_state,
            )

        if not timed_out:
            return {
                "mode_used": "exact",
                "exact": True,
                "count": exact_count,
                "message": "Exact count completed.",
            }

        if mode == "exact":
            return {
                "mode_used": "exact",
                "exact": False,
                "lower_bound": exact_count,
                "message": "Exact count timed out before completion.",
            }

    estimate, relative_error = _estimate_solution_count(
        target=target,
        size=size,
        grid=grid,
        row_sums=row_sums,
        col_sums=col_sums,
        row_unknowns=row_unknowns,
        col_unknowns=col_unknowns,
        diag_sums=diag_sums,
        diag_unknowns=diag_unknowns,
        used_values=used_values,
        max_cell_value=max_cell_value,
        unknown_positions=unknown_positions,
        sample_paths=sample_paths,
    )

    if mode == "estimate":
        return {
            "mode_used": "estimate",
            "exact": False,
            "estimated_count": estimate,
            "relative_error": relative_error,
            "message": "Estimated count using randomized search-tree sampling.",
        }

    return {
        "mode_used": "auto",
        "exact": False,
        "lower_bound": exact_count,
        "estimated_count": estimate,
        "relative_error": relative_error,
        "message": "Exact count timed out; returning lower bound plus estimate.",
    }


def _build_initial_state(
    target: int,
    size: int,
    known_grid: Optional[Grid],
    game_mode: GameMode,
) -> tuple[
    Grid,
    list[int],
    list[int],
    list[int],
    list[int],
    list[int],
    list[int],
    set[int],
    list[tuple[int, int]],
]:
    if size < 2:
        raise ValueError("size must be at least 2")
    if target <= size:
        raise ValueError("target must be greater than size")

    max_cell_value = _resolve_max_cell_value(target=target, size=size, game_mode=game_mode)
    if max_cell_value < MIN_VALUE:
        raise ValueError("No valid value range is available for this game mode and target")

    grid = _validate_and_normalize_known_grid(size=size, known_grid=known_grid, max_cell_value=max_cell_value)

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
                for diag_index in _diag_indexes(r, c, size):
                    diag_unknowns[diag_index] += 1
                unknown_positions.append((r, c))
            else:
                if value in used_values:
                    raise ValueError("known_grid cannot contain duplicate values")
                used_values.add(value)
                row_sums[r] += value
                col_sums[c] += value
                for diag_index in _diag_indexes(r, c, size):
                    diag_sums[diag_index] += value

    _validate_partial_sums(target, size, row_sums, row_unknowns, "row")
    _validate_partial_sums(target, size, col_sums, col_unknowns, "column")
    _validate_diagonal_partial_sums(target, diag_sums, diag_unknowns)

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


def _validate_global_uniqueness_feasibility(
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

    min_unknown_sum, max_unknown_sum = _min_max_sum_from_values(unused_values, unknown_count)
    required_unknown_sum = required_total - known_total
    if required_unknown_sum < min_unknown_sum or required_unknown_sum > max_unknown_sum:
        raise ValueError("known values make the unique-value total sum impossible for this target")


def _validate_and_normalize_known_grid(size: int, known_grid: Optional[Grid], max_cell_value: int) -> Grid:
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
            if value > max_cell_value:
                raise ValueError(f"known_grid integers must be at most {max_cell_value} for the selected game mode")
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


def _search_first_solution(
    grid: Grid,
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
    trace: bool,
    trace_log: Optional[TraceLog],
    depth: int,
) -> bool:
    choice = _select_next_cell_with_candidates(
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
        unknown_positions,
        grid,
    )
    if choice is None:
        _trace(trace, trace_log, f"{_indent(depth)}All cells assigned; validating final sums")
        return _final_constraints_met(target, size, row_sums, col_sums, diag_sums)

    r, c, candidates = choice
    _trace(trace, trace_log, f"{_indent(depth)}Select cell ({r}, {c}) with {len(candidates)} candidates")

    for value in candidates:
        _trace(trace, trace_log, f"{_indent(depth)}Try value {value} at ({r}, {c})")
        _apply_value(
            value,
            r,
            c,
            size,
            grid,
            row_sums,
            col_sums,
            row_unknowns,
            col_unknowns,
            diag_sums,
            diag_unknowns,
            used_values,
        )

        if _search_first_solution(
            grid=grid,
            target=target,
            size=size,
            row_sums=row_sums,
            col_sums=col_sums,
            row_unknowns=row_unknowns,
            col_unknowns=col_unknowns,
            diag_sums=diag_sums,
            diag_unknowns=diag_unknowns,
            used_values=used_values,
            max_cell_value=max_cell_value,
            unknown_positions=unknown_positions,
            trace=trace,
            trace_log=trace_log,
            depth=depth + 1,
        ):
            _trace(trace, trace_log, f"{_indent(depth)}Accept value {value} at ({r}, {c})")
            return True

        _trace(trace, trace_log, f"{_indent(depth)}Backtrack on ({r}, {c}) value {value}")
        _revert_value(
            value,
            r,
            c,
            size,
            grid,
            row_sums,
            col_sums,
            row_unknowns,
            col_unknowns,
            diag_sums,
            diag_unknowns,
            used_values,
        )

    _trace(trace, trace_log, f"{_indent(depth)}No valid values remain for ({r}, {c})")
    return False


def _count_all_solutions(
    grid: Grid,
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
    deadline: Optional[float],
    stop_requested: Optional[Callable[[], bool]],
    progress_callback: Optional[Callable[[ProgressState], None]],
    progress_interval: int,
    progress_state: dict[str, int],
) -> tuple[int, bool]:
    progress_state["nodes_visited"] += 1
    if progress_callback is not None and progress_state["nodes_visited"] % progress_interval == 0:
        progress_callback(dict(progress_state))

    if stop_requested is not None and stop_requested():
        return 0, True
    if deadline is not None and time.monotonic() >= deadline:
        return 0, True

    choice = _select_next_cell_with_candidates(
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
        unknown_positions,
        grid,
    )
    if choice is None:
        if _final_constraints_met(target, size, row_sums, col_sums, diag_sums):
            progress_state["solutions_found"] += 1
            if progress_callback is not None:
                progress_callback(dict(progress_state))
            return 1, False
        return 0, False

    r, c, candidates = choice
    if not candidates:
        return 0, False

    total = 0
    for value in candidates:
        _apply_value(
            value,
            r,
            c,
            size,
            grid,
            row_sums,
            col_sums,
            row_unknowns,
            col_unknowns,
            diag_sums,
            diag_unknowns,
            used_values,
        )

        count, timed_out = _count_all_solutions(
            grid=grid,
            target=target,
            size=size,
            row_sums=row_sums,
            col_sums=col_sums,
            row_unknowns=row_unknowns,
            col_unknowns=col_unknowns,
            diag_sums=diag_sums,
            diag_unknowns=diag_unknowns,
            used_values=used_values,
            max_cell_value=max_cell_value,
            unknown_positions=unknown_positions,
            deadline=deadline,
            stop_requested=stop_requested,
            progress_callback=progress_callback,
            progress_interval=progress_interval,
            progress_state=progress_state,
        )
        total += count

        _revert_value(
            value,
            r,
            c,
            size,
            grid,
            row_sums,
            col_sums,
            row_unknowns,
            col_unknowns,
            diag_sums,
            diag_unknowns,
            used_values,
        )

        if timed_out:
            return total, True

    return total, False


def _count_all_solutions_multiprocess(
    grid: Grid,
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
    deadline: Optional[float],
    stop_requested: Optional[Callable[[], bool]],
    progress_callback: Optional[Callable[[ProgressState], None]],
    workers: Optional[int],
    game_mode: GameMode,
) -> tuple[int, bool]:
    choice = _select_next_cell_with_candidates(
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
        unknown_positions,
        grid,
    )
    if choice is None:
        return (1, False) if _final_constraints_met(target, size, row_sums, col_sums, diag_sums) else (0, False)

    r, c, candidates = choice
    if not candidates:
        return 0, False
    if len(candidates) == 1:
        # No meaningful parallelism, keep local recursion fast.
        progress_state = {"solutions_found": 0, "nodes_visited": 0}
        return _count_all_solutions(
            grid=grid,
            target=target,
            size=size,
            row_sums=row_sums,
            col_sums=col_sums,
            row_unknowns=row_unknowns,
            col_unknowns=col_unknowns,
            diag_sums=diag_sums,
            diag_unknowns=diag_unknowns,
            used_values=used_values,
            max_cell_value=max_cell_value,
            unknown_positions=unknown_positions,
            deadline=deadline,
            stop_requested=stop_requested,
            progress_callback=progress_callback,
            progress_interval=200,
            progress_state=progress_state,
        )

    known_grids: list[Grid] = []
    for value in candidates:
        _apply_value(
            value,
            r,
            c,
            size,
            grid,
            row_sums,
            col_sums,
            row_unknowns,
            col_unknowns,
            diag_sums,
            diag_unknowns,
            used_values,
        )
        known_grids.append([row[:] for row in grid])
        _revert_value(
            value,
            r,
            c,
            size,
            grid,
            row_sums,
            col_sums,
            row_unknowns,
            col_unknowns,
            diag_sums,
            diag_unknowns,
            used_values,
        )

    total = 0
    timed_out_or_canceled = False
    worker_count = workers or max(1, (os.cpu_count() or 1) - 1)
    try:
        executor = ProcessPoolExecutor(max_workers=worker_count)
    except (PermissionError, OSError):
        progress_state = {"solutions_found": 0, "nodes_visited": 0}
        return _count_all_solutions(
            grid=grid,
            target=target,
            size=size,
            row_sums=row_sums,
            col_sums=col_sums,
            row_unknowns=row_unknowns,
            col_unknowns=col_unknowns,
            diag_sums=diag_sums,
            diag_unknowns=diag_unknowns,
            used_values=used_values,
            max_cell_value=max_cell_value,
            unknown_positions=unknown_positions,
            deadline=deadline,
            stop_requested=stop_requested,
            progress_callback=progress_callback,
            progress_interval=200,
            progress_state=progress_state,
        )

    with executor:
        futures = {
            executor.submit(
                _count_exact_subproblem_worker,
                target,
                size,
                known_grid,
                game_mode,
                None if deadline is None else max(0.0, deadline - time.monotonic()),
            ): index
            for index, known_grid in enumerate(known_grids)
        }

        while futures:
            if stop_requested is not None and stop_requested():
                timed_out_or_canceled = True
                break
            if deadline is not None and time.monotonic() >= deadline:
                timed_out_or_canceled = True
                break

            done, _ = wait(set(futures.keys()), timeout=0.1, return_when=FIRST_COMPLETED)
            if not done:
                continue

            for future in done:
                futures.pop(future, None)
                try:
                    sub_count, sub_timed_out = future.result()
                except Exception:
                    sub_count, sub_timed_out = 0, True
                total += sub_count
                if progress_callback is not None:
                    progress_callback({"solutions_found": total, "nodes_visited": 0})
                if sub_timed_out:
                    timed_out_or_canceled = True

            if timed_out_or_canceled:
                break

        if timed_out_or_canceled:
            for future in futures:
                future.cancel()

    return total, timed_out_or_canceled


def _count_exact_subproblem_worker(
    target: int,
    size: int,
    known_grid: Grid,
    game_mode: GameMode,
    max_seconds: Optional[float],
) -> tuple[int, bool]:
    try:
        result = count_solutions(
            target=target,
            size=size,
            known_grid=known_grid,
            game_mode=game_mode,
            mode="exact",
            max_seconds=max_seconds,
            sample_paths=1,
            use_multiprocessing=False,
        )
        if result["exact"]:
            return int(result["count"]), False
        return int(result.get("lower_bound", 0)), True
    except ValueError:
        # Branch became infeasible after the split; contributes zero solutions.
        return 0, False


def _estimate_solution_count(
    target: int,
    size: int,
    grid: Grid,
    row_sums: list[int],
    col_sums: list[int],
    row_unknowns: list[int],
    col_unknowns: list[int],
    diag_sums: list[int],
    diag_unknowns: list[int],
    used_values: set[int],
    max_cell_value: int,
    unknown_positions: list[tuple[int, int]],
    sample_paths: int,
) -> tuple[float, Optional[float]]:
    rng = random.Random()
    estimates: list[float] = []

    for _ in range(sample_paths):
        sim_grid = [row[:] for row in grid]
        sim_row_sums = row_sums[:]
        sim_col_sums = col_sums[:]
        sim_row_unknowns = row_unknowns[:]
        sim_col_unknowns = col_unknowns[:]
        sim_diag_sums = diag_sums[:]
        sim_diag_unknowns = diag_unknowns[:]
        sim_used_values = set(used_values)

        weight = 1.0

        while True:
            choice = _select_next_cell_with_candidates(
                target,
                size,
                sim_row_sums,
                sim_col_sums,
                sim_row_unknowns,
                sim_col_unknowns,
                sim_diag_sums,
                sim_diag_unknowns,
                sim_used_values,
                max_cell_value,
                unknown_positions,
                sim_grid,
            )
            if choice is None:
                if _final_constraints_met(target, size, sim_row_sums, sim_col_sums, sim_diag_sums):
                    estimates.append(weight)
                else:
                    estimates.append(0.0)
                break

            r, c, candidates = choice
            if not candidates:
                estimates.append(0.0)
                break

            weight *= len(candidates)
            value = rng.choice(candidates)
            _apply_value(
                value,
                r,
                c,
                size,
                sim_grid,
                sim_row_sums,
                sim_col_sums,
                sim_row_unknowns,
                sim_col_unknowns,
                sim_diag_sums,
                sim_diag_unknowns,
                sim_used_values,
            )

    mean_estimate = sum(estimates) / len(estimates)
    if len(estimates) < 2 or mean_estimate == 0:
        return mean_estimate, None

    variance = sum((value - mean_estimate) ** 2 for value in estimates) / (len(estimates) - 1)
    std_error = math.sqrt(variance / len(estimates))
    relative_error = std_error / mean_estimate
    return mean_estimate, relative_error


def _select_next_cell_with_candidates(
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
) -> Optional[tuple[int, int, list[int]]]:
    best_choice: Optional[tuple[int, int, list[int]]] = None
    best_domain_size: Optional[int] = None

    for r, c in unknown_positions:
        if grid[r][c] is not None:
            continue

        candidates = _valid_candidates_for_cell(
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


def _valid_candidates_for_cell(
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
        return []
    high = min(high, max_cell_value)

    candidates: list[int] = []
    for value in range(low, high + 1):
        if _can_place_value(
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
        row_min_sum, row_max_sum = _min_max_sum_from_values(remaining_available, row_remaining_unknowns)
        if row_remaining_sum < row_min_sum or row_remaining_sum > row_max_sum:
            return False
    if col_remaining_unknowns > 0:
        col_min_sum, col_max_sum = _min_max_sum_from_values(remaining_available, col_remaining_unknowns)
        if col_remaining_sum < col_min_sum or col_remaining_sum > col_max_sum:
            return False

    for diag_index in _diag_indexes(r, c, size):
        diag_remaining_unknowns = diag_unknowns[diag_index] - 1
        diag_after = diag_sums[diag_index] + value
        diag_remaining_sum = target - diag_after

        if diag_remaining_unknowns == 0 and diag_remaining_sum != 0:
            return False
        if diag_remaining_unknowns > 0:
            diag_min_sum, diag_max_sum = _min_max_sum_from_values(remaining_available, diag_remaining_unknowns)
            if diag_remaining_sum < diag_min_sum or diag_remaining_sum > diag_max_sum:
                return False

    return True


def _min_max_sum_from_values(values: list[int], count: int) -> tuple[int, int]:
    if count == 0:
        return 0, 0
    if len(values) < count:
        return 1, 0
    sorted_values = sorted(values)
    min_sum = sum(sorted_values[:count])
    max_sum = sum(sorted_values[-count:])
    return min_sum, max_sum


def _apply_value(
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
    for diag_index in _diag_indexes(r, c, size):
        diag_sums[diag_index] += value
        diag_unknowns[diag_index] -= 1
    used_values.add(value)


def _revert_value(
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
    for diag_index in _diag_indexes(r, c, size):
        diag_sums[diag_index] -= value
        diag_unknowns[diag_index] += 1
    used_values.remove(value)


def _final_constraints_met(
    target: int,
    size: int,
    row_sums: list[int],
    col_sums: list[int],
    diag_sums: list[int],
) -> bool:
    return (
        all(row_sums[i] == target for i in range(size))
        and all(col_sums[i] == target for i in range(size))
        and diag_sums[0] == target
        and diag_sums[1] == target
    )


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
