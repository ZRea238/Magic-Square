import { useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";
const MIN_SIZE = 2;
const MAX_SIZE = 7;

function createGrid(size, fill = "") {
  return Array.from({ length: size }, () => Array.from({ length: size }, () => fill));
}

function parseCellValue(value) {
  if (value.trim() === "") {
    return null;
  }

  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1) {
    return null;
  }

  return parsed;
}

function App() {
  const [size, setSize] = useState(3);
  const [target, setTarget] = useState(9);
  const [gridInput, setGridInput] = useState(createGrid(3));
  const [userProvided, setUserProvided] = useState(createGrid(3, false));
  const [toast, setToast] = useState(null);
  const [loading, setLoading] = useState(false);

  const rules = useMemo(
    () => [
      "Grid must be a square (N x N).",
      "Every row must sum to the target.",
      "Every column must sum to the target.",
      "Both full diagonals must sum to the target.",
      "Cell values must be integers >= 1.",
    ],
    [],
  );

  function showToast(type, message) {
    setToast({ type, message });
    window.clearTimeout(showToast.timeoutId);
    showToast.timeoutId = window.setTimeout(() => setToast(null), 3200);
  }

  function handleSizeChange(event) {
    const nextSize = Number(event.target.value);
    setSize(nextSize);
    setGridInput(createGrid(nextSize));
    setUserProvided(createGrid(nextSize, false));
    setTarget(Math.max(nextSize + 1, nextSize * 3));
  }

  function handleCellChange(rowIndex, colIndex, raw) {
    if (raw !== "" && !/^\d+$/.test(raw)) {
      return;
    }

    setGridInput((current) => {
      const next = current.map((row) => [...row]);
      next[rowIndex][colIndex] = raw;
      return next;
    });

    setUserProvided((current) => {
      const next = current.map((row) => [...row]);
      next[rowIndex][colIndex] = raw !== "";
      return next;
    });
  }

  function handleClear() {
    setGridInput(createGrid(size));
    setUserProvided(createGrid(size, false));
    showToast("info", "Grid cleared.");
  }

  async function handleSolve() {
    const numericTarget = Number(target);
    if (!Number.isInteger(numericTarget)) {
      showToast("error", "Target must be an integer.");
      return;
    }
    if (numericTarget <= size) {
      showToast("error", "Target must be greater than grid size.");
      return;
    }

    const knownGrid = gridInput.map((row) => row.map((cell) => parseCellValue(cell)));
    const hasInvalidCell = gridInput.some((row, r) =>
      row.some((cell, c) => cell.trim() !== "" && knownGrid[r][c] === null),
    );
    if (hasInvalidCell) {
      showToast("error", "All filled cells must be integers >= 1.");
      return;
    }

    const providedMask = knownGrid.map((row) => row.map((value) => value !== null));

    setLoading(true);
    showToast("info", "Solving puzzle...");

    try {
      const response = await fetch(`${API_BASE}/solve`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          target: numericTarget,
          size,
          known_grid: knownGrid,
          trace: false,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "Solver request failed.");
      }

      setGridInput(data.solution.map((row) => row.map((value) => String(value))));
      setUserProvided(providedMask);
      showToast("success", "Puzzle solved.");
    } catch (error) {
      showToast("error", error.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="hero-card">
        <h1>Magic Square Solver</h1>
        <p>
          Welcome. Define your puzzle, fill any cells you know, and let the solver complete the rest while keeping
          every row, column, and diagonal at the target.
        </p>
      </section>

      <section className="layout-grid">
        <aside className="panel">
          <h2>Game Rules</h2>
          <ul>
            {rules.map((rule) => (
              <li key={rule}>{rule}</li>
            ))}
          </ul>

          <div className="controls">
            <label>
              Grid Size
              <select value={size} onChange={handleSizeChange} disabled={loading}>
                {Array.from({ length: MAX_SIZE - MIN_SIZE + 1 }, (_, i) => i + MIN_SIZE).map((value) => (
                  <option key={value} value={value}>
                    {value} x {value}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Target
              <input
                type="number"
                min={size + 1}
                value={target}
                onChange={(event) => setTarget(event.target.value)}
                disabled={loading}
              />
            </label>
          </div>

          <div className="legend">
            <span className="chip chip-user">Your value</span>
            <span className="chip chip-solved">Solver value</span>
          </div>

          <div className="actions">
            <button className="btn btn-secondary" onClick={handleClear} disabled={loading}>
              Clear
            </button>
            <button className="btn btn-primary" onClick={handleSolve} disabled={loading}>
              {loading ? "Solving..." : "Solve"}
            </button>
          </div>
        </aside>

        <section className="panel board-panel">
          <h2>Puzzle Grid</h2>
          <div className="board" style={{ gridTemplateColumns: `repeat(${size}, minmax(0, 1fr))` }}>
            {gridInput.map((row, rowIndex) =>
              row.map((cell, colIndex) => (
                <input
                  key={`${rowIndex}-${colIndex}`}
                  className={`cell ${userProvided[rowIndex][colIndex] ? "cell-user" : "cell-solved"}`}
                  value={cell}
                  onChange={(event) => handleCellChange(rowIndex, colIndex, event.target.value)}
                  inputMode="numeric"
                  disabled={loading}
                  aria-label={`Cell ${rowIndex + 1}, ${colIndex + 1}`}
                />
              )),
            )}
          </div>
        </section>
      </section>

      {toast ? <div className={`toast toast-${toast.type}`}>{toast.message}</div> : null}
    </main>
  );
}

export default App;
