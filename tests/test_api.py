import unittest

try:
    from api import app
except ModuleNotFoundError:
    app = None

try:
    from fastapi.testclient import TestClient
except (ImportError, RuntimeError):
    TestClient = None


@unittest.skipIf(app is None or TestClient is None, "fastapi stack is not available in this environment")
class TestApiIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_endpoint(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_solve_endpoint_returns_solution_and_grid_format(self) -> None:
        response = self.client.post(
            "/solve",
            json={
                "target": 9,
                "size": 3,
                "known_grid": [
                    [None, 3, None],
                    [3, None, None],
                    [None, None, None],
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("solution", body)
        self.assertIn("grid_rows", body)
        self.assertIn("grid_text", body)
        self.assertEqual(body["grid_rows"], ["3 3 3", "3 3 3", "3 3 3"])
        self.assertEqual(body["grid_text"], "3 3 3\n3 3 3\n3 3 3")

    def test_solve_endpoint_with_trace_includes_trace(self) -> None:
        response = self.client.post(
            "/solve",
            json={
                "target": 6,
                "size": 2,
                "trace": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("trace", body)
        self.assertTrue(len(body["trace"]) > 0)
        self.assertTrue(any("Select cell" in line for line in body["trace"]))

    def test_solve_endpoint_returns_400_on_invalid_puzzle(self) -> None:
        response = self.client.post(
            "/solve",
            json={
                "target": 3,
                "size": 3,
            },
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn("detail", body)


if __name__ == "__main__":
    unittest.main()
