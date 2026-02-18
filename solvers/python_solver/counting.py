import math
import os
import random
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from typing import Callable, Optional

from .constraints import select_next_cell_with_candidates
from .search import count_all_solutions
from .state import apply_value, build_initial_state, final_constraints_met, revert_value
from .types import GameMode, Grid, ProgressState
from .validation import resolve_max_cell_value, validate_global_uniqueness_feasibility


def count_all_solutions_multiprocess(
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
    choice = select_next_cell_with_candidates(
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
        return (1, False) if final_constraints_met(target, size, row_sums, col_sums, diag_sums) else (0, False)

    r, c, candidates = choice
    if not candidates:
        return 0, False

    if len(candidates) == 1:
        progress_state = {"solutions_found": 0, "nodes_visited": 0}
        return count_all_solutions(
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
        apply_value(
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
        revert_value(
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
        return count_all_solutions(
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
                count_exact_subproblem_worker,
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


def count_exact_subproblem_worker(
    target: int,
    size: int,
    known_grid: Grid,
    game_mode: GameMode,
    max_seconds: Optional[float],
) -> tuple[int, bool]:
    try:
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
        ) = build_initial_state(target=target, size=size, known_grid=known_grid, game_mode=game_mode)
        max_cell_value = resolve_max_cell_value(target=target, size=size, game_mode=game_mode)
        validate_global_uniqueness_feasibility(target, size, grid, used_values, max_cell_value)

        deadline = None if max_seconds is None else time.monotonic() + max_seconds
        progress_state = {"solutions_found": 0, "nodes_visited": 0}
        count, timed_out = count_all_solutions(
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
            stop_requested=None,
            progress_callback=None,
            progress_interval=200,
            progress_state=progress_state,
        )
        return count, timed_out
    except ValueError:
        return 0, False


def estimate_solution_count(
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
            choice = select_next_cell_with_candidates(
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
                if final_constraints_met(target, size, sim_row_sums, sim_col_sums, sim_diag_sums):
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
            apply_value(
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
