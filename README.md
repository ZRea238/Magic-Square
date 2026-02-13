# Magic-Square
A repo containing the code for the magic square solver

Rules: each row, column, and both full diagonals must equal the target, and every value in the grid must be unique.

Game modes:
- `unbounded`: values can be any positive integers (subject to puzzle constraints)
- `bounded_by_size_squared`: values must be `<= size^2` (for 5x5, max value is 25)

## Run API (FastAPI + Uvicorn)

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the API server:

```bash
uvicorn api:app --reload
```

Open interactive docs:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

Example `POST /solve` request body:

```json
{
  "target": 15,
  "size": 3,
  "game_mode": "unbounded",
  "known_grid": [
    [8, null, null],
    [null, 5, null],
    [null, null, 2]
  ],
  "trace": true
}
```

## Run Frontend (React + Vite)

From the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open: `http://127.0.0.1:5173`

The frontend calls the API at `http://127.0.0.1:8000` by default.
To override it, set `VITE_API_BASE` before starting Vite, for example:

```bash
VITE_API_BASE=http://localhost:8000 npm run dev
```

Frontend JSON loading:

- Upload your own puzzle JSON file directly from the browser UI.
- Load bundled examples from `frontend/public/examples`:
  - `easy-3x3.json`
  - `medium-4x4.json`
  - `hard-5x5.json`

Example response body:

```json
{
  "solution": [
    [8, 1, 6],
    [3, 5, 7],
    [4, 9, 2]
  ],
  "grid_rows": [
    "8 1 6",
    "3 5 7",
    "4 9 2"
  ],
  "grid_text": "8 1 6\n3 5 7\n4 9 2",
  "trace": []
}
```

Example `POST /count` request body:

```json
{
  "target": 15,
  "size": 3,
  "game_mode": "unbounded",
  "known_grid": [
    [8, null, null],
    [null, 5, null],
    [null, null, 2]
  ],
  "mode": "auto",
  "max_seconds": 2.5,
  "sample_paths": 300,
  "use_multiprocessing": true,
  "workers": 4
}
```

Example `POST /count` response body:

```json
{
  "mode_used": "auto",
  "exact": false,
  "lower_bound": 0,
  "estimated_count": 1.21,
  "relative_error": 0.31,
  "message": "Exact count timed out; returning lower bound plus estimate."
}
```

For long-running counts with progress/cancel support:

1. `POST /count/jobs/start` to start a background job
2. `GET /count/jobs/{job_id}` to read status, `lower_bound`, and `elapsed_seconds`
3. `POST /count/jobs/{job_id}/cancel` to stop the job and keep the latest lower bound

## Solve From JSON

Run the solver with a JSON file:

```bash
python main.py --input puzzle.json
```

Include trace output:

```bash
python main.py --input puzzle.json --trace
```

Example input file:

```json
{
  "target": 15,
  "size": 3,
  "game_mode": "unbounded",
  "known_grid": [
    [8, null, null],
    [null, 5, null],
    [null, null, 2]
  ]
}
```

## Running tests

Run all unit tests with:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Tests are also run automatically in GitHub Actions on every push and pull request.
