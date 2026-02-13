import argparse
import json
from pathlib import Path
from solver.solver import solve_square
from typing import Any, Optional
from rules.rules import MIN_VALUE


def run(target: int, size: int, known_grid: Optional[list[list[Optional[int]]]] = None) -> list[list[int]]:
    # boundary validation
    if not isinstance(target, int):
        raise ValueError("target must be an integer")
    if not isinstance(size, int):
        raise ValueError("size must be an integer")
    if size < 2:
        raise ValueError("size must be at least 2")
    if target <= size:
        raise ValueError("target must be greater than size")
    if known_grid is not None:
        if not isinstance(known_grid, list) or len(known_grid) != size:
            raise ValueError("known_grid must be a square list with length equal to size")
        for row in known_grid:
            if not isinstance(row, list) or len(row) != size:
                raise ValueError("known_grid must be a square list with length equal to size")
            for value in row:
                if value is None:
                    continue
                if not isinstance(value, int):
                    raise ValueError("known_grid entries must be integers or None")
                if value < MIN_VALUE:
                    raise ValueError(f"known_grid integers must be at least {MIN_VALUE}")

    return solve_square(target=target, size=size, known_grid=known_grid)


def run_with_trace(
    target: int,
    size: int,
    known_grid: Optional[list[list[Optional[int]]]] = None,
) -> tuple[list[list[int]], list[str]]:
    trace_log: list[str] = []
    result = solve_square(target=target, size=size, known_grid=known_grid, trace=True, trace_log=trace_log)
    return result, trace_log


def load_puzzle_from_file(input_path: str) -> tuple[int, int, Optional[list[list[Optional[int]]]]]:
    path = Path(input_path)
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"input file not found: {input_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"input file is not valid JSON: {input_path}") from exc

    if not isinstance(payload, dict):
        raise ValueError("JSON root must be an object")

    target = payload.get("target")
    size = payload.get("size")
    known_grid = payload.get("known_grid")
    if target is None:
        raise ValueError("JSON must include 'target'")
    if size is None:
        raise ValueError("JSON must include 'size'")
    if known_grid is None:
        return target, size, None

    return target, size, known_grid


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Solve the square sum puzzle from a JSON input file")
    parser.add_argument("--input", required=True, help="Path to a JSON file with target, size, and optional known_grid")
    parser.add_argument("--trace", action="store_true", help="Include solver trace output")
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()

    try:
        target, size, known_grid = load_puzzle_from_file(args.input)
        if args.trace:
            solution, trace_log = run_with_trace(target=target, size=size, known_grid=known_grid)
            print(json.dumps({"solution": solution, "trace": trace_log}, indent=2))
        else:
            solution = run(target=target, size=size, known_grid=known_grid)
            print(json.dumps({"solution": solution}, indent=2))
    except ValueError as exc:
        raise SystemExit(f"Error: {exc}")
