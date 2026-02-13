import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";
const MIN_SIZE = 2;
const MAX_SIZE = 7;
const GAME_MODES = ["unbounded", "bounded_by_size_squared"];
const SAMPLE_FILES = [
  { label: "Easy 3x3", path: "/examples/easy-3x3.json" },
  { label: "Medium 4x4", path: "/examples/medium-4x4.json" },
  { label: "Hard 5x5", path: "/examples/hard-5x5.json" },
];

function defaultTargetForSize(size) {
  return (size * (size * size + 1)) / 2;
}

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

function normalizeKnownGrid(rawGrid, size) {
  if (rawGrid === undefined || rawGrid === null) {
    return createGrid(size, null);
  }

  if (!Array.isArray(rawGrid) || rawGrid.length !== size) {
    throw new Error(`known_grid must be a ${size}x${size} array.`);
  }

  return rawGrid.map((row, rowIndex) => {
    if (!Array.isArray(row) || row.length !== size) {
      throw new Error(`known_grid must be a ${size}x${size} array.`);
    }

    return row.map((cell, colIndex) => {
      if (cell === null || cell === "") {
        return null;
      }

      const parsed = Number(cell);
      if (!Number.isInteger(parsed) || parsed < 1) {
        throw new Error(`Cell (${rowIndex + 1}, ${colIndex + 1}) must be an integer >= 1 or null.`);
      }
      return parsed;
    });
  });
}

function parsePuzzleJson(rawData) {
  if (!rawData || typeof rawData !== "object" || Array.isArray(rawData)) {
    throw new Error("Puzzle JSON must be an object.");
  }

  const parsedSize = Number(rawData.size);
  if (!Number.isInteger(parsedSize) || parsedSize < MIN_SIZE || parsedSize > MAX_SIZE) {
    throw new Error(`size must be an integer between ${MIN_SIZE} and ${MAX_SIZE}.`);
  }

  const parsedTarget = Number(rawData.target);
  if (!Number.isInteger(parsedTarget) || parsedTarget <= parsedSize) {
    throw new Error("target must be an integer greater than size.");
  }

  const parsedGameMode = rawData.game_mode ?? "unbounded";
  if (!GAME_MODES.includes(parsedGameMode)) {
    throw new Error(`game_mode must be one of: ${GAME_MODES.join(", ")}.`);
  }

  const rawGrid = rawData.known_grid ?? rawData.grid;
  const knownGrid = normalizeKnownGrid(rawGrid, parsedSize);

  return {
    size: parsedSize,
    target: parsedTarget,
    gameMode: parsedGameMode,
    knownGrid,
  };
}

function App() {
  const [size, setSize] = useState(3);
  const [target, setTarget] = useState(defaultTargetForSize(3));
  const [gridInput, setGridInput] = useState(createGrid(3));
  const [userProvided, setUserProvided] = useState(createGrid(3, false));
  const [gameMode, setGameMode] = useState("unbounded");
  const [countInfo, setCountInfo] = useState(null);
  const [runToCompletion, setRunToCompletion] = useState(false);
  const [countMaxSeconds, setCountMaxSeconds] = useState(30);
  const [useMultiprocessing, setUseMultiprocessing] = useState(false);
  const [workerCount, setWorkerCount] = useState("");
  const [selectedSamplePath, setSelectedSamplePath] = useState(SAMPLE_FILES[0].path);
  const [toast, setToast] = useState(null);
  const [loading, setLoading] = useState(false);
  const [counting, setCounting] = useState(false);
  const countAbortControllerRef = useRef(null);
  const countPollIntervalRef = useRef(null);
  const activeCountJobIdRef = useRef(null);

  function applyPuzzleConfig(puzzleConfig, sourceLabel) {
    if (counting) {
      handleCancelCount();
    }

    const nextGridInput = puzzleConfig.knownGrid.map((row) => row.map((value) => (value === null ? "" : String(value))));
    const nextUserProvided = puzzleConfig.knownGrid.map((row) => row.map((value) => value !== null));

    setSize(puzzleConfig.size);
    setTarget(puzzleConfig.target);
    setGameMode(puzzleConfig.gameMode);
    setGridInput(nextGridInput);
    setUserProvided(nextUserProvided);
    setCountInfo(null);
    setRunToCompletion(false);
    setUseMultiprocessing(false);
    setWorkerCount("");
    showToast("success", `Loaded puzzle from ${sourceLabel}.`);
  }

  const rules = useMemo(
    () => [
      "Grid must be a square (N x N).",
      "Every row must sum to the target.",
      "Every column must sum to the target.",
      "Both full diagonals must sum to the target.",
      "Every value must be unique (no repeats).",
      "Cell values must be integers >= 1.",
    ],
    [],
  );

  function showToast(type, message, persistent = false) {
    setToast({ type, message });
    window.clearTimeout(showToast.timeoutId);
    if (!persistent) {
      showToast.timeoutId = window.setTimeout(() => setToast(null), 3200);
    }
  }

  function clearCountPolling() {
    if (countPollIntervalRef.current) {
      window.clearInterval(countPollIntervalRef.current);
      countPollIntervalRef.current = null;
    }
  }

  function handleSizeChange(event) {
    const nextSize = Number(event.target.value);
    setSize(nextSize);
    setGridInput(createGrid(nextSize));
    setUserProvided(createGrid(nextSize, false));
    setTarget(defaultTargetForSize(nextSize));
    setCountInfo(null);
    setRunToCompletion(false);
    setUseMultiprocessing(false);
    setWorkerCount("");
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
    if (counting) {
      handleCancelCount();
    }
    setGridInput(createGrid(size));
    setUserProvided(createGrid(size, false));
    setCountInfo(null);
    setRunToCompletion(false);
    setUseMultiprocessing(false);
    setWorkerCount("");
    setGameMode("unbounded");
    showToast("info", "Grid cleared.");
  }

  async function handleLocalFileLoad(event) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    try {
      const rawText = await file.text();
      const parsedJson = JSON.parse(rawText);
      const puzzleConfig = parsePuzzleJson(parsedJson);
      applyPuzzleConfig(puzzleConfig, file.name);
    } catch (error) {
      showToast("error", error.message || "Unable to load file.");
    } finally {
      event.target.value = "";
    }
  }

  async function handleSampleLoad() {
    if (!selectedSamplePath) {
      showToast("error", "Select a sample file first.");
      return;
    }

    try {
      const response = await fetch(selectedSamplePath);
      if (!response.ok) {
        throw new Error("Unable to load sample file.");
      }
      const parsedJson = await response.json();
      const puzzleConfig = parsePuzzleJson(parsedJson);
      const sampleLabel = SAMPLE_FILES.find((sample) => sample.path === selectedSamplePath)?.label ?? "sample file";
      applyPuzzleConfig(puzzleConfig, sampleLabel);
    } catch (error) {
      showToast("error", error.message || "Unable to load sample file.");
    }
  }

  function handleDownloadPuzzle() {
    try {
      const numericTarget = validateTarget();
      const knownGrid = buildKnownGrid();
      const payload = {
        size,
        target: numericTarget,
        game_mode: gameMode,
        known_grid: knownGrid,
      };

      const blob = new Blob([JSON.stringify(payload, null, 2)], {
        type: "application/json",
      });
      const downloadUrl = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = downloadUrl;
      anchor.download = `magic-square-${size}x${size}-target-${numericTarget}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      window.URL.revokeObjectURL(downloadUrl);
      showToast("success", "Puzzle JSON downloaded.");
    } catch (error) {
      showToast("error", error.message || "Unable to download puzzle JSON.");
    }
  }

  function buildKnownGrid(onlyUserProvided = false) {
    const knownGrid = gridInput.map((row, rowIndex) =>
      row.map((cell, colIndex) => {
        if (onlyUserProvided && !userProvided[rowIndex][colIndex]) {
          return null;
        }
        return parseCellValue(cell);
      }),
    );
    const hasInvalidCell = gridInput.some((row, r) =>
      row.some((cell, c) => {
        if (onlyUserProvided && !userProvided[r][c]) {
          return false;
        }
        return cell.trim() !== "" && knownGrid[r][c] === null;
      }),
    );
    if (hasInvalidCell) {
      throw new Error("All filled cells must be integers >= 1.");
    }
    return knownGrid;
  }

  function validateTarget() {
    const numericTarget = Number(target);
    if (!Number.isInteger(numericTarget)) {
      throw new Error("Target must be an integer.");
    }
    if (numericTarget <= size) {
      throw new Error("Target must be greater than grid size.");
    }
    return numericTarget;
  }

  async function handleSolve() {
    let numericTarget;
    let knownGrid;
    try {
      numericTarget = validateTarget();
      knownGrid = buildKnownGrid();
    } catch (error) {
      showToast("error", error.message);
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
          game_mode: gameMode,
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

  async function handleCountSolutions() {
    let numericTarget;
    let knownGrid;
    let numericMaxSeconds;
    let numericWorkerCount = null;
    try {
      numericTarget = validateTarget();
      knownGrid = buildKnownGrid(true);
      numericMaxSeconds = Number(countMaxSeconds);
      if (!runToCompletion) {
        if (!Number.isFinite(numericMaxSeconds) || numericMaxSeconds <= 0) {
          throw new Error("Max count time must be a positive number of seconds.");
        }
      }
      if (useMultiprocessing && workerCount !== "") {
        numericWorkerCount = Number(workerCount);
        if (!Number.isInteger(numericWorkerCount) || numericWorkerCount <= 0) {
          throw new Error("Worker count must be a positive integer.");
        }
      }
    } catch (error) {
      showToast("error", error.message);
      return;
    }

    if (runToCompletion) {
      const confirmed = window.confirm("Run until all solutions are found? This can take a very long time on larger grids.");
      if (!confirmed) {
        return;
      }
    }

    try {
      const abortController = new AbortController();
      countAbortControllerRef.current = abortController;
      const response = await fetch(`${API_BASE}/count/jobs/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        signal: abortController.signal,
        body: JSON.stringify({
          target: numericTarget,
          size,
          known_grid: knownGrid,
          game_mode: gameMode,
          mode: runToCompletion ? "exact" : "auto",
          max_seconds: runToCompletion ? null : numericMaxSeconds,
          sample_paths: 300,
          use_multiprocessing: useMultiprocessing,
          workers: numericWorkerCount,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "Count request failed.");
      }

      activeCountJobIdRef.current = data.job_id;
      setCounting(true);
      clearCountPolling();
      showToast(
        "info",
        runToCompletion
          ? "Counting all solutions (no time limit). The solver is thinking..."
          : `Counting solutions (up to ${numericMaxSeconds}s exact + estimate fallback)...`,
        true,
      );

      countPollIntervalRef.current = window.setInterval(async () => {
        try {
          const statusResponse = await fetch(`${API_BASE}/count/jobs/${activeCountJobIdRef.current}`);
          const statusData = await statusResponse.json();
          if (!statusResponse.ok) {
            throw new Error(statusData.detail ?? "Unable to fetch count status.");
          }

          setCountInfo(statusData);

          if (["completed", "canceled", "failed"].includes(statusData.status)) {
            clearCountPolling();
            setCounting(false);
            if (statusData.status === "completed") {
              if (statusData.exact) {
                showToast("success", `Exact solution count: ${statusData.count}`);
              } else {
                showToast("info", "Count completed with estimate.");
              }
            } else if (statusData.status === "canceled") {
              showToast("info", `Counting canceled. Latest lower bound: ${statusData.lower_bound ?? 0}`);
            } else {
              showToast("error", statusData.error ?? "Counting failed.");
            }
          }
        } catch (pollError) {
          clearCountPolling();
          setCounting(false);
          showToast("error", pollError.message);
        }
      }, 1000);
    } catch (error) {
      if (error.name === "AbortError") {
        showToast("info", "Counting canceled.");
        return;
      }
      showToast("error", error.message);
    } finally {
      countAbortControllerRef.current = null;
    }
  }

  function handleCancelCount() {
    if (!counting || !activeCountJobIdRef.current) {
      return;
    }
    fetch(`${API_BASE}/count/jobs/${activeCountJobIdRef.current}/cancel`, {
      method: "POST",
    }).catch(() => {
      showToast("error", "Unable to send cancel request.");
    });
    showToast("info", "Cancel requested. Waiting for solver to stop...", true);
  }

  function renderCountText() {
    if (!countInfo) {
      return "Solution count will appear here.";
    }
    if (countInfo.status === "running" || countInfo.status === "canceling" || countInfo.status === "queued") {
      return `Status: ${countInfo.status}. Lower bound so far: ${countInfo.lower_bound ?? 0}. Elapsed: ${Math.round(
        countInfo.elapsed_seconds ?? 0,
      )}s. Nodes visited: ${countInfo.nodes_visited ?? 0}.`;
    }
    if (countInfo.exact) {
      return `Exact solutions: ${countInfo.count}.`;
    }
    if (countInfo.mode_used === "auto") {
      const estimate = countInfo.estimated_count?.toFixed(2) ?? "N/A";
      const errorPct =
        countInfo.relative_error !== null && countInfo.relative_error !== undefined
          ? ` ± ${(countInfo.relative_error * 100).toFixed(1)}%`
          : "";
      return `Lower bound: ${countInfo.lower_bound ?? 0}. Estimated solutions: ${estimate}${errorPct}.`;
    }
    if (countInfo.mode_used === "estimate") {
      const estimate = countInfo.estimated_count?.toFixed(2) ?? "N/A";
      const errorPct =
        countInfo.relative_error !== null && countInfo.relative_error !== undefined
          ? ` ± ${(countInfo.relative_error * 100).toFixed(1)}%`
          : "";
      return `Estimated solutions: ${estimate}${errorPct}.`;
    }
    return `Lower bound: ${countInfo.lower_bound ?? 0}.`;
  }

  useEffect(() => {
    return () => {
      clearCountPolling();
      if (countAbortControllerRef.current) {
        countAbortControllerRef.current.abort();
      }
    };
  }, []);

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
            <label>
              Game Mode
              <select value={gameMode} onChange={(event) => setGameMode(event.target.value)} disabled={loading || counting}>
                <option value="unbounded">Unbounded Values</option>
                <option value="bounded_by_size_squared">Bounded by Size Squared</option>
              </select>
            </label>
          </div>
          <div className="import-tools">
            <h3>Load Puzzle JSON</h3>
            <label className="file-input-label">
              Upload From Your Computer
              <input type="file" accept="application/json,.json" onChange={handleLocalFileLoad} disabled={loading || counting} />
            </label>
            <label>
              Example Puzzles
              <select
                value={selectedSamplePath}
                onChange={(event) => setSelectedSamplePath(event.target.value)}
                disabled={loading || counting}
              >
                {SAMPLE_FILES.map((sample) => (
                  <option key={sample.path} value={sample.path}>
                    {sample.label}
                  </option>
                ))}
              </select>
            </label>
            <button className="btn btn-secondary" onClick={handleSampleLoad} disabled={loading || counting}>
              Load Example
            </button>
            <button className="btn btn-secondary" onClick={handleDownloadPuzzle} disabled={loading || counting}>
              Download Current Puzzle JSON
            </button>
            <p>Format: {`{"size": 3, "target": 15, "game_mode": "unbounded", "known_grid": [[8, null, null], ...]}`}</p>
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
          <div className="actions actions-count">
            <button className="btn btn-secondary" onClick={handleCountSolutions} disabled={loading || counting}>
              {counting ? "Counting..." : "Count Solutions"}
            </button>
            {counting ? (
              <button className="btn btn-danger" onClick={handleCancelCount}>
                Cancel Count
              </button>
            ) : null}
          </div>
          <label className="toggle-wrap">
            <input
              type="checkbox"
              checked={runToCompletion}
              onChange={(event) => setRunToCompletion(event.target.checked)}
              disabled={loading || counting}
            />
            <span>Run until all solutions are found (exact, no timeout)</span>
          </label>
          <label className="count-limit-label">
            <span>Max Count Time (seconds)</span>
            <input
              type="number"
              min="1"
              step="1"
              value={countMaxSeconds}
              onChange={(event) => setCountMaxSeconds(event.target.value)}
              disabled={loading || counting || runToCompletion}
            />
          </label>
          <label className="toggle-wrap">
            <input
              type="checkbox"
              checked={useMultiprocessing}
              onChange={(event) => setUseMultiprocessing(event.target.checked)}
              disabled={loading || counting}
            />
            <span>Use multiprocessing for counting</span>
          </label>
          <label className="count-limit-label">
            <span>Worker Processes (optional)</span>
            <input
              type="number"
              min="1"
              step="1"
              value={workerCount}
              onChange={(event) => setWorkerCount(event.target.value)}
              placeholder="auto"
              disabled={loading || counting || !useMultiprocessing}
            />
          </label>
          {runToCompletion ? (
            <p className="warning-text">
              Warning: exact exhaustive counting can take a very long time for larger grids.
            </p>
          ) : null}
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
          <div className="count-display">
            <h3>Total Possible Solutions</h3>
            <p>{renderCountText()}</p>
            {countInfo ? <small>{countInfo.message ?? ""}</small> : null}
          </div>
        </section>
      </section>

      {toast ? <div className={`toast toast-${toast.type}`}>{toast.message}</div> : null}
    </main>
  );
}

export default App;
