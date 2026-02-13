# Magic-Square
A repo containing the code for the magic square solver

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
  "target": 9,
  "size": 3,
  "known_grid": [
    [null, 3, null],
    [3, null, null],
    [null, null, null]
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

Example response body:

```json
{
  "solution": [
    [3, 3, 3],
    [3, 3, 3],
    [3, 3, 3]
  ],
  "grid_rows": [
    "3 3 3",
    "3 3 3",
    "3 3 3"
  ],
  "grid_text": "3 3 3\n3 3 3\n3 3 3",
  "trace": []
}
```

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
  "target": 9,
  "size": 3,
  "known_grid": [
    [null, 3, null],
    [3, null, null],
    [null, null, null]
  ]
}
```

## Running tests

Run all unit tests with:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Tests are also run automatically in GitHub Actions on every push and pull request.
