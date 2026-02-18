import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .solver import solve_square
from .types import Grid, SolvedGrid, TraceLog, TraceStep


LANGUAGES = ["python", "go", "cpp"]
SOLVE_METHODS = [
    "mrv_backtracking",
    "mrv_backtracking_with_propagation",
    "mrv_backtracking_randomized",
    "mrv_backtracking_with_propagation_randomized",
    "exhaustive_backtracking",
    "exhaustive_backtracking_randomized",
]


def supported_solver_catalog() -> dict[str, dict[str, dict[str, object]]]:
    return {
        "python": {
            "mrv_backtracking": {"implemented": True, "entrypoint": "solvers/python_solver/main.py"},
            "mrv_backtracking_with_propagation": {"implemented": True, "entrypoint": "solvers/python_solver/main.py"},
            "mrv_backtracking_randomized": {"implemented": True, "entrypoint": "solvers/python_solver/main.py"},
            "mrv_backtracking_with_propagation_randomized": {
                "implemented": True,
                "entrypoint": "solvers/python_solver/main.py",
            },
            "exhaustive_backtracking": {"implemented": True, "entrypoint": "solvers/python_solver/main.py"},
            "exhaustive_backtracking_randomized": {"implemented": True, "entrypoint": "solvers/python_solver/main.py"},
        },
        "go": {
            "mrv_backtracking": {"implemented": True, "binary_env": "GO_SOLVER_BIN", "entrypoint": "solvers/go_solver/main.go"},
            "mrv_backtracking_with_propagation": {
                "implemented": True,
                "binary_env": "GO_SOLVER_BIN",
                "entrypoint": "solvers/go_solver/main.go",
            },
            "mrv_backtracking_randomized": {
                "implemented": True,
                "binary_env": "GO_SOLVER_BIN",
                "entrypoint": "solvers/go_solver/main.go",
            },
            "mrv_backtracking_with_propagation_randomized": {
                "implemented": True,
                "binary_env": "GO_SOLVER_BIN",
                "entrypoint": "solvers/go_solver/main.go",
            },
            "exhaustive_backtracking": {
                "implemented": True,
                "binary_env": "GO_SOLVER_BIN",
                "entrypoint": "solvers/go_solver/main.go",
            },
            "exhaustive_backtracking_randomized": {
                "implemented": True,
                "binary_env": "GO_SOLVER_BIN",
                "entrypoint": "solvers/go_solver/main.go",
            },
        },
        "cpp": {
            "mrv_backtracking": {
                "implemented": True,
                "binary_env": "CPP_SOLVER_BIN",
                "entrypoint": "solvers/cpp_solver/main.cpp",
            },
            "mrv_backtracking_with_propagation": {
                "implemented": True,
                "binary_env": "CPP_SOLVER_BIN",
                "entrypoint": "solvers/cpp_solver/main.cpp",
            },
            "mrv_backtracking_randomized": {
                "implemented": True,
                "binary_env": "CPP_SOLVER_BIN",
                "entrypoint": "solvers/cpp_solver/main.cpp",
            },
            "mrv_backtracking_with_propagation_randomized": {
                "implemented": True,
                "binary_env": "CPP_SOLVER_BIN",
                "entrypoint": "solvers/cpp_solver/main.cpp",
            },
            "exhaustive_backtracking": {
                "implemented": True,
                "binary_env": "CPP_SOLVER_BIN",
                "entrypoint": "solvers/cpp_solver/main.cpp",
            },
            "exhaustive_backtracking_randomized": {
                "implemented": True,
                "binary_env": "CPP_SOLVER_BIN",
                "entrypoint": "solvers/cpp_solver/main.cpp",
            },
        },
    }


def runtime_capabilities() -> dict[str, dict[str, object]]:
    go_env = os.getenv("GO_SOLVER_BIN")
    cpp_env = os.getenv("CPP_SOLVER_BIN")
    go_on_path = shutil.which("go")
    gpp_on_path = shutil.which("g++")
    go_source = os.path.join(_repo_root(), "solvers", "go_solver", "main.go")
    cpp_source = os.path.join(_repo_root(), "solvers", "cpp_solver", "main.cpp")

    go_available = bool((go_env and os.path.exists(go_env)) or (go_on_path and os.path.exists(go_source)))
    cpp_available = bool((cpp_env and os.path.exists(cpp_env)) or (gpp_on_path and os.path.exists(cpp_source)))

    return {
        "python": {
            "available": True,
            "reason": "Built into API process.",
        },
        "go": {
            "available": go_available,
            "reason": (
                f"Using GO_SOLVER_BIN={go_env}"
                if go_env
                else ("Using go toolchain from PATH." if go_on_path else "Go toolchain not found on PATH.")
            ),
        },
        "cpp": {
            "available": cpp_available,
            "reason": (
                f"Using CPP_SOLVER_BIN={cpp_env}"
                if cpp_env
                else ("Using g++ toolchain from PATH." if gpp_on_path else "g++ not found on PATH.")
            ),
        },
    }


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _go_command() -> list[str]:
    configured = os.getenv("GO_SOLVER_BIN")
    if configured:
        return [configured]

    go_exe = shutil.which("go")
    if go_exe is None:
        raise ValueError(
            "go solver is not configured. Install Go and ensure 'go' is on PATH, or set GO_SOLVER_BIN."
        )
    source_dir = Path(_repo_root()) / "solvers" / "go_solver"
    source_files = sorted(str(path) for path in source_dir.glob("*.go"))
    if not source_files:
        raise ValueError("go solver source files not found")
    output_path = os.path.join("/tmp", "magic_square_go_solver")
    needs_build = True
    if os.path.exists(output_path):
        latest_source_mtime = max(os.path.getmtime(path) for path in source_files)
        needs_build = os.path.getmtime(output_path) < latest_source_mtime

    if needs_build:
        completed = subprocess.run(
            [go_exe, "build", "-o", output_path, *source_files],
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
        if completed.returncode != 0:
            raise ValueError(
                f"failed to build go solver: {completed.stderr.strip() or 'go build returned non-zero exit'}"
            )

    return [output_path]


def _cpp_command() -> list[str]:
    configured = os.getenv("CPP_SOLVER_BIN")
    if configured:
        return [configured]

    compiler = shutil.which("g++")
    if compiler is None:
        raise ValueError(
            "cpp solver is not configured. Install g++ and ensure it is on PATH, or set CPP_SOLVER_BIN."
        )

    source_dir = Path(_repo_root()) / "solvers" / "cpp_solver"
    source_files = [str(path) for path in sorted(source_dir.glob("*.cpp"))]
    source_files.extend(str(path) for path in sorted((source_dir / "src").glob("*.cpp")))
    include_dir = source_dir / "include"
    if not source_files:
        raise ValueError("cpp solver source files not found")
    output_path = os.path.join("/tmp", "magic_square_cpp_solver")
    needs_build = True
    if os.path.exists(output_path):
        latest_source_mtime = max(os.path.getmtime(path) for path in source_files)
        needs_build = os.path.getmtime(output_path) < latest_source_mtime

    if needs_build:
        completed = subprocess.run(
            [compiler, "-std=c++17", "-O2", "-I", str(include_dir), *source_files, "-o", output_path],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if completed.returncode != 0:
            raise ValueError(
                f"failed to build cpp solver: {completed.stderr.strip() or 'compiler returned non-zero exit'}"
            )

    return [output_path]


def solve_with_engine(
    target: int,
    size: int,
    known_grid: Optional[Grid],
    game_mode: str,
    language: str,
    solve_method: str,
    trace: bool = False,
    trace_log: Optional[TraceLog] = None,
    trace_steps: Optional[list[TraceStep]] = None,
    trace_meta: Optional[dict[str, bool]] = None,
    trace_max_steps: int = 1000,
) -> SolvedGrid:
    catalog = supported_solver_catalog()

    if language not in catalog:
        raise ValueError(f"language must be one of: {', '.join(LANGUAGES)}")
    if solve_method not in catalog[language]:
        raise ValueError(
            f"solve_method '{solve_method}' is not supported for language '{language}'. "
            f"Supported methods: {', '.join(sorted(catalog[language].keys()))}"
        )

    if language == "python":
        return solve_square(
            target=target,
            size=size,
            known_grid=known_grid,
            game_mode=game_mode,
            solve_method=solve_method,
            trace=trace,
            trace_log=trace_log,
            trace_steps=trace_steps,
            trace_meta=trace_meta,
            trace_max_steps=trace_max_steps,
        )

    if trace or trace_steps is not None:
        raise ValueError(f"trace output is currently available only for language='python'")

    command: list[str]
    if language == "go":
        command = _go_command()
    elif language == "cpp":
        command = _cpp_command()
    else:
        raise ValueError("unsupported language")

    payload = {
        "target": target,
        "size": size,
        "known_grid": known_grid,
        "game_mode": game_mode,
        "solve_method": solve_method,
        "language": language,
    }

    try:
        completed = subprocess.run(
            command,
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
    except OSError as exc:
        raise ValueError(f"failed to execute {language} solver command '{' '.join(command)}': {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f"{language} solver timed out") from exc

    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        raise ValueError(f"{language} solver failed (exit {completed.returncode}): {stderr or 'no stderr output'}")

    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{language} solver returned invalid JSON") from exc

    solution = parsed.get("solution")
    if not isinstance(solution, list):
        raise ValueError(f"{language} solver response must include a 'solution' array")

    return solution
