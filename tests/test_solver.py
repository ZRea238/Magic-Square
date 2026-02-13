import unittest

from rules.rules import MIN_VALUE
from solver.solver import count_solutions, solve_square


class TestSolveSquare(unittest.TestCase):
    def test_solves_3x3_without_known_values(self) -> None:
        result = solve_square(target=15, size=3)
        self.assert_square_constraints(result, target=15)
        self.assert_unique_values(result)

    def test_solves_3x3_with_known_values(self) -> None:
        known_grid = [
            [8, None, None],
            [None, 5, None],
            [None, None, 2],
        ]
        result = solve_square(target=15, size=3, known_grid=known_grid)
        self.assertEqual(result[0][0], 8)
        self.assertEqual(result[1][1], 5)
        self.assertEqual(result[2][2], 2)
        self.assert_square_constraints(result, target=15)
        self.assert_all_values_at_least_min(result)
        self.assert_unique_values(result)

    def test_returns_fully_known_grid_when_already_solved(self) -> None:
        known_grid = [
            [8, 1, 6],
            [3, 5, 7],
            [4, 9, 2],
        ]
        result = solve_square(target=15, size=3, known_grid=known_grid)
        self.assertEqual(result, known_grid)

    def test_raises_when_target_is_not_greater_than_size(self) -> None:
        with self.assertRaises(ValueError):
            solve_square(target=3, size=3)

    def test_raises_when_size_is_too_small(self) -> None:
        with self.assertRaises(ValueError):
            solve_square(target=6, size=1)

    def test_raises_when_known_grid_is_not_square(self) -> None:
        with self.assertRaises(ValueError):
            solve_square(target=15, size=3, known_grid=[[1, 2], [3, 4]])

    def test_raises_when_known_value_is_below_minimum(self) -> None:
        with self.assertRaises(ValueError):
            solve_square(target=15, size=3, known_grid=[[0, None, None], [None, None, None], [None, None, None]])

    def test_raises_when_known_grid_contains_duplicate_values(self) -> None:
        with self.assertRaises(ValueError):
            solve_square(target=15, size=3, known_grid=[[8, 1, 6], [3, 5, 7], [4, 8, None]])

    def test_raises_when_known_grid_is_inconsistent(self) -> None:
        with self.assertRaises(ValueError):
            solve_square(target=15, size=3, known_grid=[[8, 1, 9], [None, None, None], [None, None, None]])

    def test_raises_when_no_solution_exists(self) -> None:
        with self.assertRaises(ValueError):
            solve_square(target=6, size=2)

    def test_trace_mode_records_search_steps(self) -> None:
        trace_log: list[str] = []
        result = solve_square(target=15, size=3, trace=True, trace_log=trace_log)
        self.assert_square_constraints(result, target=15)
        self.assert_unique_values(result)
        self.assertTrue(len(trace_log) > 0)
        self.assertTrue(any("Select cell" in line for line in trace_log))
        self.assertTrue(any("Try value" in line for line in trace_log))

    def test_raises_when_diagonal_is_inconsistent(self) -> None:
        with self.assertRaises(ValueError):
            solve_square(target=15, size=3, known_grid=[[9, None, None], [None, 5, None], [None, None, 9]])

    def test_solves_in_bounded_mode(self) -> None:
        result = solve_square(target=15, size=3, game_mode="bounded_by_size_squared")
        self.assert_square_constraints(result, target=15)
        self.assert_unique_values(result)
        self.assertTrue(all(value <= 9 for row in result for value in row))

    def test_raises_in_bounded_mode_when_known_value_exceeds_bound(self) -> None:
        with self.assertRaises(ValueError):
            solve_square(target=40, size=3, known_grid=[[10, None, None], [None, None, None], [None, None, None]], game_mode="bounded_by_size_squared")

    def test_count_exact_for_3x3_magic_square(self) -> None:
        result = count_solutions(target=15, size=3, mode="exact", max_seconds=5.0)
        self.assertTrue(result["exact"])
        self.assertEqual(result["count"], 8)

    def test_count_exact_with_no_timeout_completes(self) -> None:
        result = count_solutions(target=15, size=3, mode="exact", max_seconds=None)
        self.assertTrue(result["exact"])
        self.assertEqual(result["count"], 8)

    def test_count_exact_with_multiprocessing_completes(self) -> None:
        result = count_solutions(
            target=15,
            size=3,
            mode="exact",
            max_seconds=5.0,
            use_multiprocessing=True,
            workers=2,
        )
        self.assertTrue(result["exact"])
        self.assertEqual(result["count"], 8)

    def test_count_estimate_returns_estimate_value(self) -> None:
        result = count_solutions(target=15, size=3, mode="estimate", sample_paths=80)
        self.assertFalse(result["exact"])
        self.assertIn("estimated_count", result)
        self.assertGreaterEqual(result["estimated_count"], 0)

    def test_count_auto_returns_partial_when_timed_out(self) -> None:
        result = count_solutions(target=15, size=3, mode="auto", max_seconds=0.0, sample_paths=60)
        self.assertFalse(result["exact"])
        self.assertEqual(result["mode_used"], "auto")
        self.assertIn("lower_bound", result)
        self.assertIn("estimated_count", result)

    def assert_square_constraints(self, grid: list[list[int]], target: int) -> None:
        for row in grid:
            self.assertEqual(sum(row), target)
        for column in zip(*grid):
            self.assertEqual(sum(column), target)
        self.assertEqual(sum(grid[i][i] for i in range(len(grid))), target)
        self.assertEqual(sum(grid[i][len(grid) - 1 - i] for i in range(len(grid))), target)

    def assert_all_values_at_least_min(self, grid: list[list[int]]) -> None:
        for row in grid:
            for value in row:
                self.assertGreaterEqual(value, MIN_VALUE)

    def assert_unique_values(self, grid: list[list[int]]) -> None:
        flattened = [value for row in grid for value in row]
        self.assertEqual(len(flattened), len(set(flattened)))


if __name__ == "__main__":
    unittest.main()
