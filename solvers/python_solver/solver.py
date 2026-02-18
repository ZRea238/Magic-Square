import time
from typing import Callable, Optional

from .counting import count_all_solutions_multiprocess, estimate_solution_count
from .search import (
    count_all_solutions,
    search_first_solution,
    search_first_solution_exhaustive,
    search_first_solution_with_propagation,
)
from .state import build_initial_state
from .types import CountResult, GameMode, Grid, ProgressState, SolvedGrid, TraceLog, TraceStep
from .utils import trace as emit_trace
from .validation import resolve_max_cell_value, validate_count_options, validate_global_uniqueness_feasibility

SOLVE_METHODS = {
    "mrv_backtracking",
    "mrv_backtracking_with_propagation",
    "mrv_backtracking_randomized",
    "mrv_backtracking_with_propagation_randomized",
    "exhaustive_backtracking",
    "exhaustive_backtracking_randomized",
}


def solve_square(
    target: int,
    size: int,
    known_grid: Optional[Grid] = None,
    game_mode: GameMode = "unbounded",
    solve_method: str = "mrv_backtracking",
    trace: bool = False,
    trace_log: Optional[TraceLog] = None,
    trace_steps: Optional[list[TraceStep]] = None,
    trace_meta: Optional[dict[str, bool]] = None,
    trace_max_steps: int = 1000,
) -> SolvedGrid:
    if trace_max_steps < 1:
        raise ValueError("trace_max_steps must be >= 1")
    if solve_method not in SOLVE_METHODS:
        raise ValueError(f"solve_method must be one of: {', '.join(sorted(SOLVE_METHODS))}")

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

    emit_trace(
        trace,
        trace_log,
        f"Initialized search: size={size}, target={target}, unknown_cells={len(unknown_positions)}, method={solve_method}",
    )

    if solve_method in {"mrv_backtracking", "mrv_backtracking_randomized"}:
        solved = search_first_solution(
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
            trace_enabled=trace,
            trace_log=trace_log,
            trace_steps=trace_steps,
            trace_meta=trace_meta,
            trace_max_steps=trace_max_steps,
            randomized=solve_method == "mrv_backtracking_randomized",
            depth=0,
        )
    elif solve_method in {"exhaustive_backtracking", "exhaustive_backtracking_randomized"}:
        solved = search_first_solution_exhaustive(
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
            trace_enabled=trace,
            trace_log=trace_log,
            trace_steps=trace_steps,
            trace_meta=trace_meta,
            trace_max_steps=trace_max_steps,
            randomized=solve_method == "exhaustive_backtracking_randomized",
            depth=0,
        )
    else:
        solved = search_first_solution_with_propagation(
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
            trace_enabled=trace,
            trace_log=trace_log,
            trace_steps=trace_steps,
            trace_meta=trace_meta,
            trace_max_steps=trace_max_steps,
            randomized=solve_method == "mrv_backtracking_with_propagation_randomized",
            depth=0,
        )

    if not solved:
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
    validate_count_options(
        game_mode=game_mode,
        mode=mode,
        max_seconds=max_seconds,
        sample_paths=sample_paths,
        progress_interval=progress_interval,
        workers=workers,
    )

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

    if mode in {"auto", "exact"}:
        deadline = None if max_seconds is None else time.monotonic() + max_seconds
        progress_state: ProgressState = {"solutions_found": 0, "nodes_visited": 0}

        if use_multiprocessing:
            exact_count, timed_out = count_all_solutions_multiprocess(
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
            exact_count, timed_out = count_all_solutions(
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

    estimate, relative_error = estimate_solution_count(
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
