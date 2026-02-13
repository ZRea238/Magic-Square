from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from solver.solver import solve_square


class SolveRequest(BaseModel):
    target: int = Field(..., description="Required sum for every row, column, and main diagonals")
    size: int = Field(..., description="Side length of the square grid")
    known_grid: Optional[list[list[Optional[int]]]] = Field(
        default=None,
        description="Square grid with integers for known values and null for unknown values",
    )
    trace: bool = Field(default=False, description="Include solver trace output in the response")


class SolveResponse(BaseModel):
    solution: list[list[int]]
    grid_rows: list[str]
    grid_text: str
    trace: Optional[list[str]] = None


app = FastAPI(
    title="Magic Square Solver API",
    description="Solve square grid puzzles where each row, column, and both full diagonals equal the target.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/solve", response_model=SolveResponse)
def solve(request: SolveRequest) -> SolveResponse:
    try:
        if request.trace:
            trace_log: list[str] = []
            solution = solve_square(
                target=request.target,
                size=request.size,
                known_grid=request.known_grid,
                trace=True,
                trace_log=trace_log,
            )
            grid_rows = _format_grid_rows(solution)
            return SolveResponse(solution=solution, grid_rows=grid_rows, grid_text="\n".join(grid_rows), trace=trace_log)

        solution = solve_square(
            target=request.target,
            size=request.size,
            known_grid=request.known_grid,
        )
        grid_rows = _format_grid_rows(solution)
        return SolveResponse(solution=solution, grid_rows=grid_rows, grid_text="\n".join(grid_rows))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _format_grid_rows(solution: list[list[int]]) -> list[str]:
    return [" ".join(str(value) for value in row) for row in solution]
