import threading
import time
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from solvers.python_solver.engines import LANGUAGES, SOLVE_METHODS, runtime_capabilities, solve_with_engine, supported_solver_catalog
from solvers.python_solver.solver import count_solutions


class SolveRequest(BaseModel):
    target: int = Field(..., description="Required sum for every row, column, and both full diagonals")
    size: int = Field(..., description="Side length of the square grid")
    known_grid: Optional[list[list[Optional[int]]]] = Field(
        default=None,
        description="Square grid with integers for known values and null for unknown values",
    )
    game_mode: str = Field(
        default="unbounded",
        description="Game mode: unbounded or bounded_by_size_squared.",
    )
    language: str = Field(default="python", description="Solver language: python, go, or cpp.")
    solve_method: str = Field(
        default="mrv_backtracking",
        description=(
            "Solve method: mrv_backtracking, mrv_backtracking_with_propagation, "
            "mrv_backtracking_randomized, mrv_backtracking_with_propagation_randomized, "
            "exhaustive_backtracking, or exhaustive_backtracking_randomized."
        ),
    )
    trace: bool = Field(default=False, description="Include solver trace output in the response")
    trace_steps: bool = Field(default=False, description="Include structured trace steps for walkthrough/debugging.")
    trace_max_steps: int = Field(default=1000, ge=1, le=20000, description="Maximum number of trace steps to return.")


class TraceStepResponse(BaseModel):
    event: str
    message: str
    depth: int
    row: Optional[int] = None
    col: Optional[int] = None
    value: Optional[int] = None
    candidates: Optional[list[int]] = None
    grid: list[list[Optional[int]]]


class SolveResponse(BaseModel):
    solution: list[list[int]]
    grid_rows: list[str]
    grid_text: str
    trace: Optional[list[str]] = None
    trace_steps: Optional[list[TraceStepResponse]] = None
    trace_truncated: bool = False


class CountRequest(BaseModel):
    target: int = Field(..., description="Required sum for every row, column, and both full diagonals")
    size: int = Field(..., description="Side length of the square grid")
    known_grid: Optional[list[list[Optional[int]]]] = Field(
        default=None,
        description="Square grid with integers for known values and null for unknown values",
    )
    game_mode: str = Field(
        default="unbounded",
        description="Game mode: unbounded or bounded_by_size_squared.",
    )
    mode: str = Field(default="auto", description="Counting mode: auto, exact, or estimate")
    max_seconds: Optional[float] = Field(
        default=2.0,
        ge=0.0,
        description="Time budget for exact counting in auto/exact mode. Use null to run exact mode to completion.",
    )
    sample_paths: int = Field(default=300, ge=1, description="Number of randomized paths used in estimate mode")
    use_multiprocessing: bool = Field(
        default=False,
        description="Enable process-based parallel counting for exact/auto modes.",
    )
    workers: Optional[int] = Field(
        default=None,
        ge=1,
        description="Number of worker processes to use when multiprocessing is enabled.",
    )


class CountResponse(BaseModel):
    mode_used: str
    exact: bool
    count: Optional[int] = None
    lower_bound: Optional[int] = None
    estimated_count: Optional[float] = None
    relative_error: Optional[float] = None
    message: str


class BenchmarkRequest(BaseModel):
    target: int = Field(..., description="Required sum for every row, column, and both full diagonals")
    size: int = Field(..., description="Side length of the square grid")
    known_grid: Optional[list[list[Optional[int]]]] = Field(
        default=None,
        description="Square grid with integers for known values and null for unknown values",
    )
    game_mode: str = Field(default="unbounded", description="Game mode.")
    languages: list[str] = Field(default_factory=lambda: ["python", "go", "cpp"])
    solve_methods: list[str] = Field(
        default_factory=lambda: [
            "mrv_backtracking",
            "mrv_backtracking_with_propagation",
            "mrv_backtracking_randomized",
            "mrv_backtracking_with_propagation_randomized",
            "exhaustive_backtracking",
            "exhaustive_backtracking_randomized",
        ]
    )
    repeat: int = Field(default=1, ge=1, le=5, description="Number of repetitions for each language/method combo.")
    warmup_runs: int = Field(default=1, ge=0, le=5, description="Number of warmup runs before timed repeats.")


class BenchmarkItem(BaseModel):
    language: str
    solve_method: str
    ok: bool
    elapsed_ms: Optional[float] = None
    error: Optional[str] = None


class BenchmarkResponse(BaseModel):
    results: list[BenchmarkItem]


class CountJobStartResponse(BaseModel):
    job_id: str
    status: str


class CountJobStatusResponse(BaseModel):
    job_id: str
    status: str
    elapsed_seconds: float
    mode_requested: str
    nodes_visited: int
    exact: Optional[bool] = None
    count: Optional[int] = None
    lower_bound: Optional[int] = None
    estimated_count: Optional[float] = None
    relative_error: Optional[float] = None
    message: Optional[str] = None
    error: Optional[str] = None


app = FastAPI(
    title="Magic Square Solver API",
    description="Solve square grid puzzles where each row, column, and both full diagonals equal the target with unique values.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_COUNT_JOBS: dict[str, dict] = {}
_COUNT_JOBS_LOCK = threading.Lock()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/solve/catalog")
def solve_catalog() -> dict[str, object]:
    return {
        "languages": LANGUAGES,
        "methods": SOLVE_METHODS,
        "catalog": supported_solver_catalog(),
        "capabilities": runtime_capabilities(),
    }


@app.post("/solve", response_model=SolveResponse)
def solve(request: SolveRequest) -> SolveResponse:
    try:
        if request.trace or request.trace_steps:
            trace_log: list[str] = []
            trace_steps: list[dict[str, object]] = []
            trace_meta = {"truncated": False}
            solution = solve_with_engine(
                target=request.target,
                size=request.size,
                known_grid=request.known_grid,
                game_mode=request.game_mode,
                language=request.language,
                solve_method=request.solve_method,
                trace=request.trace or request.trace_steps,
                trace_log=trace_log,
                trace_steps=trace_steps if request.trace_steps else None,
                trace_meta=trace_meta,
                trace_max_steps=request.trace_max_steps,
            )
            grid_rows = _format_grid_rows(solution)
            return SolveResponse(
                solution=solution,
                grid_rows=grid_rows,
                grid_text="\n".join(grid_rows),
                trace=trace_log if request.trace else None,
                trace_steps=trace_steps if request.trace_steps else None,
                trace_truncated=trace_meta["truncated"],
            )

        solution = solve_with_engine(
            target=request.target,
            size=request.size,
            known_grid=request.known_grid,
            game_mode=request.game_mode,
            language=request.language,
            solve_method=request.solve_method,
        )
        grid_rows = _format_grid_rows(solution)
        return SolveResponse(solution=solution, grid_rows=grid_rows, grid_text="\n".join(grid_rows))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/count", response_model=CountResponse)
def count(request: CountRequest) -> CountResponse:
    try:
        result = count_solutions(
            target=request.target,
            size=request.size,
            known_grid=request.known_grid,
            game_mode=request.game_mode,
            mode=request.mode,
            max_seconds=request.max_seconds,
            sample_paths=request.sample_paths,
            use_multiprocessing=request.use_multiprocessing,
            workers=request.workers,
        )
        return CountResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/solve/benchmark", response_model=BenchmarkResponse)
def solve_benchmark(request: BenchmarkRequest) -> BenchmarkResponse:
    results: list[BenchmarkItem] = []
    for language in request.languages:
        for solve_method in request.solve_methods:
            best_ms: Optional[float] = None
            last_error: Optional[str] = None
            ok = True

            for _ in range(request.warmup_runs):
                try:
                    solve_with_engine(
                        target=request.target,
                        size=request.size,
                        known_grid=request.known_grid,
                        game_mode=request.game_mode,
                        language=language,
                        solve_method=solve_method,
                        trace=False,
                    )
                except ValueError as exc:
                    ok = False
                    last_error = str(exc)
                    break

            if not ok:
                results.append(
                    BenchmarkItem(
                        language=language,
                        solve_method=solve_method,
                        ok=False,
                        elapsed_ms=None,
                        error=last_error,
                    )
                )
                continue

            for _ in range(request.repeat):
                started = time.perf_counter()
                try:
                    solve_with_engine(
                        target=request.target,
                        size=request.size,
                        known_grid=request.known_grid,
                        game_mode=request.game_mode,
                        language=language,
                        solve_method=solve_method,
                        trace=False,
                    )
                    elapsed_ms = (time.perf_counter() - started) * 1000.0
                    if best_ms is None or elapsed_ms < best_ms:
                        best_ms = elapsed_ms
                except ValueError as exc:
                    ok = False
                    last_error = str(exc)
                    break

            results.append(
                BenchmarkItem(
                    language=language,
                    solve_method=solve_method,
                    ok=ok,
                    elapsed_ms=best_ms if ok else None,
                    error=last_error,
                )
            )

    return BenchmarkResponse(results=results)


@app.post("/count/jobs/start", response_model=CountJobStartResponse, status_code=status.HTTP_202_ACCEPTED)
def count_start(request: CountRequest) -> CountJobStartResponse:
    job_id = str(uuid.uuid4())
    created_at = time.time()
    job = {
        "job_id": job_id,
        "status": "queued",
        "created_at": created_at,
        "started_at": None,
        "completed_at": None,
        "request": request.model_dump(),
        "result": None,
        "lower_bound": 0,
        "nodes_visited": 0,
        "error": None,
        "cancel_event": threading.Event(),
    }

    with _COUNT_JOBS_LOCK:
        _COUNT_JOBS[job_id] = job

    thread = threading.Thread(target=_run_count_job, args=(job_id,), daemon=True)
    thread.start()

    return CountJobStartResponse(job_id=job_id, status="queued")


@app.get("/count/jobs/{job_id}", response_model=CountJobStatusResponse)
def count_status(job_id: str) -> CountJobStatusResponse:
    with _COUNT_JOBS_LOCK:
        job = _COUNT_JOBS.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="count job not found")
        return _build_job_status_response(job)


@app.post("/count/jobs/{job_id}/cancel", response_model=CountJobStatusResponse)
def count_cancel(job_id: str) -> CountJobStatusResponse:
    with _COUNT_JOBS_LOCK:
        job = _COUNT_JOBS.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="count job not found")
        if job["status"] in {"completed", "canceled", "failed"}:
            return _build_job_status_response(job)
        job["cancel_event"].set()
        if job["status"] == "queued":
            job["status"] = "canceled"
            job["completed_at"] = time.time()
        elif job["status"] == "running":
            job["status"] = "canceling"
        return _build_job_status_response(job)


def _run_count_job(job_id: str) -> None:
    with _COUNT_JOBS_LOCK:
        job = _COUNT_JOBS.get(job_id)
        if job is None:
            return
        if job["status"] == "canceled":
            return
        job["status"] = "running"
        job["started_at"] = time.time()
        request_data = job["request"]
        cancel_event = job["cancel_event"]

    def on_progress(progress: dict[str, int]) -> None:
        with _COUNT_JOBS_LOCK:
            in_memory_job = _COUNT_JOBS.get(job_id)
            if in_memory_job is None:
                return
            in_memory_job["lower_bound"] = progress.get("solutions_found", in_memory_job["lower_bound"])
            in_memory_job["nodes_visited"] = max(
                in_memory_job["nodes_visited"],
                progress.get("nodes_visited", in_memory_job["nodes_visited"]),
            )

    try:
        result = count_solutions(
            target=request_data["target"],
            size=request_data["size"],
            known_grid=request_data["known_grid"],
            game_mode=request_data.get("game_mode", "unbounded"),
            mode=request_data["mode"],
            max_seconds=request_data["max_seconds"],
            sample_paths=request_data["sample_paths"],
            stop_requested=cancel_event.is_set,
            progress_callback=on_progress,
            use_multiprocessing=request_data.get("use_multiprocessing", False),
            workers=request_data.get("workers"),
        )
    except ValueError as exc:
        with _COUNT_JOBS_LOCK:
            in_memory_job = _COUNT_JOBS.get(job_id)
            if in_memory_job is None:
                return
            in_memory_job["status"] = "failed"
            in_memory_job["error"] = str(exc)
            in_memory_job["completed_at"] = time.time()
        return
    except Exception as exc:  # pragma: no cover
        with _COUNT_JOBS_LOCK:
            in_memory_job = _COUNT_JOBS.get(job_id)
            if in_memory_job is None:
                return
            in_memory_job["status"] = "failed"
            in_memory_job["error"] = f"unexpected error: {exc}"
            in_memory_job["completed_at"] = time.time()
        return

    with _COUNT_JOBS_LOCK:
        in_memory_job = _COUNT_JOBS.get(job_id)
        if in_memory_job is None:
            return
        in_memory_job["result"] = result
        if cancel_event.is_set():
            in_memory_job["status"] = "canceled"
            in_memory_job["result"]["exact"] = False
            in_memory_job["result"]["count"] = None
            in_memory_job["result"]["lower_bound"] = in_memory_job["lower_bound"]
            in_memory_job["result"]["message"] = "Count canceled. Returning latest lower bound."
        else:
            in_memory_job["status"] = "completed"
            if "lower_bound" in result and result["lower_bound"] is not None:
                in_memory_job["lower_bound"] = int(result["lower_bound"])
            elif "count" in result and result["count"] is not None:
                in_memory_job["lower_bound"] = int(result["count"])
        in_memory_job["completed_at"] = time.time()


def _build_job_status_response(job: dict) -> CountJobStatusResponse:
    now = time.time()
    if job["started_at"] is None:
        elapsed_seconds = 0.0
    elif job["completed_at"] is None:
        elapsed_seconds = now - job["started_at"]
    else:
        elapsed_seconds = job["completed_at"] - job["started_at"]

    result = job["result"] or {}
    lower_bound = result.get("lower_bound", job.get("lower_bound", 0))
    if lower_bound is None:
        lower_bound = job.get("lower_bound", 0)

    return CountJobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        elapsed_seconds=elapsed_seconds,
        mode_requested=job["request"]["mode"],
        nodes_visited=job.get("nodes_visited", 0),
        exact=result.get("exact"),
        count=result.get("count"),
        lower_bound=lower_bound,
        estimated_count=result.get("estimated_count"),
        relative_error=result.get("relative_error"),
        message=result.get("message"),
        error=job.get("error"),
    )


def _format_grid_rows(solution: list[list[int]]) -> list[str]:
    return [" ".join(str(value) for value in row) for row in solution]
