import unittest

from rules.rules import MIN_VALUE
from solver.solver import solve_square


class TestSolveSquare(unittest.TestCase):
    def test_solves_2x2_without_known_values(self) -> None:
        result = solve_square(target=6, size=2)
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]), 2)
        self.assert_square_constraints(result, target=6)

    def test_solves_3x3_with_known_values(self) -> None:
        known_grid = [
            [None, 3, None],
            [3, None, None],
            [None, None, None],
        ]
        result = solve_square(target=9, size=3, known_grid=known_grid)
        self.assertEqual(result[0][1], 3)
        self.assertEqual(result[1][0], 3)
        self.assert_square_constraints(result, target=9)
        self.assert_all_values_at_least_min(result)

    def test_returns_fully_known_grid_when_already_solved(self) -> None:
        known_grid = [
            [3, 3],
            [3, 3],
        ]
        result = solve_square(target=6, size=2, known_grid=known_grid)
        self.assertEqual(result, known_grid)

    def test_raises_when_target_is_not_greater_than_size(self) -> None:
        with self.assertRaises(ValueError):
            solve_square(target=3, size=3)

    def test_raises_when_size_is_too_small(self) -> None:
        with self.assertRaises(ValueError):
            solve_square(target=6, size=1)

    def test_raises_when_known_grid_is_not_square(self) -> None:
        with self.assertRaises(ValueError):
            solve_square(target=8, size=3, known_grid=[[1, 2], [3, 4]])

    def test_raises_when_known_value_is_below_minimum(self) -> None:
        with self.assertRaises(ValueError):
            solve_square(target=8, size=3, known_grid=[[0, None, None], [None, None, None], [None, None, None]])

    def test_raises_when_known_grid_is_inconsistent(self) -> None:
        with self.assertRaises(ValueError):
            solve_square(target=7, size=3, known_grid=[[6, 2, None], [None, None, None], [None, None, None]])

    def test_raises_when_no_solution_exists(self) -> None:
        with self.assertRaises(ValueError):
            solve_square(target=5, size=2, known_grid=[[1, 1], [4, None]])

    def test_trace_mode_records_search_steps(self) -> None:
        trace_log: list[str] = []
        result = solve_square(target=6, size=2, trace=True, trace_log=trace_log)
        self.assert_square_constraints(result, target=6)
        self.assertTrue(len(trace_log) > 0)
        self.assertTrue(any("Select cell" in line for line in trace_log))
        self.assertTrue(any("Try value" in line for line in trace_log))

    def test_raises_when_diagonal_is_inconsistent(self) -> None:
        with self.assertRaises(ValueError):
            solve_square(target=5, size=2, known_grid=[[1, None], [None, 1]])

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


if __name__ == "__main__":
    unittest.main()
