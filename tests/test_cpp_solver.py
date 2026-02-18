import json
import shutil
import subprocess
import unittest
from pathlib import Path


GPP_EXE = shutil.which("g++")
REPO_ROOT = Path(__file__).resolve().parent.parent
CPP_DIR = REPO_ROOT / "solvers" / "cpp_solver"
CPP_INCLUDE = CPP_DIR / "include"
CPP_SOURCES = [str(path) for path in sorted(CPP_DIR.glob("*.cpp"))]
CPP_SOURCES.extend(str(path) for path in sorted((CPP_DIR / "src").glob("*.cpp")))
CPP_BIN = Path("/tmp/magic_square_cpp_solver_test")
METHODS = [
    "mrv_backtracking",
    "mrv_backtracking_with_propagation",
    "mrv_backtracking_randomized",
    "mrv_backtracking_with_propagation_randomized",
    "exhaustive_backtracking",
    "exhaustive_backtracking_randomized",
]


def assert_magic_square(testcase: unittest.TestCase, grid: list[list[int]], target: int) -> None:
    for row in grid:
        testcase.assertEqual(sum(row), target)
    for col in zip(*grid):
        testcase.assertEqual(sum(col), target)
    testcase.assertEqual(sum(grid[i][i] for i in range(len(grid))), target)
    testcase.assertEqual(sum(grid[i][len(grid) - 1 - i] for i in range(len(grid))), target)
    flat = [v for row in grid for v in row]
    testcase.assertEqual(len(flat), len(set(flat)))


@unittest.skipIf(GPP_EXE is None, "g++ toolchain not installed")
class TestCppSolver(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        compile_result = subprocess.run(
            [GPP_EXE, "-std=c++17", "-O2", "-I", str(CPP_INCLUDE), *CPP_SOURCES, "-o", str(CPP_BIN)],
            text=True,
            capture_output=True,
            check=False,
        )
        if compile_result.returncode != 0:
            raise unittest.SkipTest(f"Unable to compile C++ solver: {compile_result.stderr}")

    def run_cpp_solver(self, payload: dict) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(CPP_BIN)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_solves_known_3x3_for_all_methods(self) -> None:
        base = {
            "target": 15,
            "size": 3,
            "known_grid": [[8, None, None], [None, 5, None], [None, None, 2]],
            "game_mode": "unbounded",
            "language": "cpp",
        }
        for method in METHODS:
            payload = dict(base)
            payload["solve_method"] = method
            result = self.run_cpp_solver(payload)
            self.assertEqual(result.returncode, 0, msg=f"method={method}, stderr={result.stderr}")
            body = json.loads(result.stdout)
            solution = body["solution"]
            assert_magic_square(self, solution, target=15)
            self.assertEqual(solution[0][0], 8)
            self.assertEqual(solution[1][1], 5)
            self.assertEqual(solution[2][2], 2)

    def test_supports_bounded_mode(self) -> None:
        payload = {
            "target": 15,
            "size": 3,
            "known_grid": None,
            "game_mode": "bounded_by_size_squared",
            "language": "cpp",
            "solve_method": "mrv_backtracking",
        }
        result = self.run_cpp_solver(payload)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        body = json.loads(result.stdout)
        solution = body["solution"]
        assert_magic_square(self, solution, target=15)
        self.assertTrue(all(v <= 9 for row in solution for v in row))

    def test_rejects_unknown_method(self) -> None:
        payload = {
            "target": 15,
            "size": 3,
            "known_grid": None,
            "game_mode": "unbounded",
            "language": "cpp",
            "solve_method": "not_a_method",
        }
        result = self.run_cpp_solver(payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported solve_method", result.stderr)

    def test_rejects_duplicate_known_values(self) -> None:
        payload = {
            "target": 15,
            "size": 3,
            "known_grid": [[8, 1, 6], [3, 5, 7], [4, 8, None]],
            "game_mode": "unbounded",
            "language": "cpp",
            "solve_method": "mrv_backtracking",
        }
        result = self.run_cpp_solver(payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate", result.stderr.lower())

    def test_rejects_unsatisfiable_board(self) -> None:
        payload = {
            "target": 6,
            "size": 2,
            "known_grid": None,
            "game_mode": "unbounded",
            "language": "cpp",
            "solve_method": "mrv_backtracking",
        }
        result = self.run_cpp_solver(payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No valid solution", result.stderr)


if __name__ == "__main__":
    unittest.main()
