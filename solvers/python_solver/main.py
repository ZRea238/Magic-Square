import json
import sys
from typing import Any

from solvers.python_solver.solver import solve_square


def _read_request() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        raise ValueError("empty request")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("request must be a JSON object")
    return payload


def main() -> int:
    try:
        request = _read_request()
        target = request.get("target")
        size = request.get("size")
        known_grid = request.get("known_grid")
        game_mode = request.get("game_mode", "unbounded")
        solve_method = request.get("solve_method", "mrv_backtracking")

        solution = solve_square(
            target=target,
            size=size,
            known_grid=known_grid,
            game_mode=game_mode,
            solve_method=solve_method,
            trace=False,
        )
        print(json.dumps({"solution": solution}))
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
