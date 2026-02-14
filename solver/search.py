import time
from typing import Callable, Optional

from .constraints import select_next_cell_with_candidates
from .state import apply_value, final_constraints_met, revert_value
from .types import Grid, ProgressState, TraceLog, TraceStep
from .utils import indent, trace


def search_first_solution(
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
    trace_enabled: bool,
    trace_log: Optional[TraceLog],
    trace_steps: Optional[list[TraceStep]],
    trace_meta: Optional[dict[str, bool]],
    trace_max_steps: int,
    depth: int,
) -> bool:
    def record_step(
        event: str,
        message: str,
        row: Optional[int] = None,
        col: Optional[int] = None,
        value: Optional[int] = None,
        candidates: Optional[list[int]] = None,
    ) -> None:
        if trace_steps is None:
            return
        if len(trace_steps) >= trace_max_steps:
            if trace_meta is not None:
                trace_meta["truncated"] = True
            return
        trace_steps.append(
            {
                "event": event,
                "message": message,
                "depth": depth,
                "row": row,
                "col": col,
                "value": value,
                "candidates": candidates,
                "grid": [grid_row[:] for grid_row in grid],
            }
        )

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
        message = f"{indent(depth)}All cells assigned; validating final sums"
        trace(trace_enabled, trace_log, message)
        record_step("validate_complete", message)
        return final_constraints_met(target, size, row_sums, col_sums, diag_sums)

    r, c, candidates = choice
    message = f"{indent(depth)}Select cell ({r}, {c}) with {len(candidates)} candidates"
    trace(trace_enabled, trace_log, message)
    record_step("select_cell", message, row=r, col=c, candidates=candidates)

    for value in candidates:
        message = f"{indent(depth)}Try value {value} at ({r}, {c})"
        trace(trace_enabled, trace_log, message)
        record_step("try_value", message, row=r, col=c, value=value)
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

        if search_first_solution(
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
            trace_enabled=trace_enabled,
            trace_log=trace_log,
            trace_steps=trace_steps,
            trace_meta=trace_meta,
            trace_max_steps=trace_max_steps,
            depth=depth + 1,
        ):
            message = f"{indent(depth)}Accept value {value} at ({r}, {c})"
            trace(trace_enabled, trace_log, message)
            record_step("accept_value", message, row=r, col=c, value=value)
            return True

        message = f"{indent(depth)}Backtrack on ({r}, {c}) value {value}"
        trace(trace_enabled, trace_log, message)
        record_step("backtrack", message, row=r, col=c, value=value)
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

    message = f"{indent(depth)}No valid values remain for ({r}, {c})"
    trace(trace_enabled, trace_log, message)
    record_step("prune_branch", message, row=r, col=c)
    return False


def count_all_solutions(
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
    progress_state: ProgressState,
) -> tuple[int, bool]:
    progress_state["nodes_visited"] += 1
    if progress_callback is not None and progress_state["nodes_visited"] % progress_interval == 0:
        progress_callback(dict(progress_state))

    if stop_requested is not None and stop_requested():
        return 0, True
    if deadline is not None and time.monotonic() >= deadline:
        return 0, True

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
        if final_constraints_met(target, size, row_sums, col_sums, diag_sums):
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
            stop_requested=stop_requested,
            progress_callback=progress_callback,
            progress_interval=progress_interval,
            progress_state=progress_state,
        )
        total += count

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

        if timed_out:
            return total, True

    return total, False
