import unittest
import time

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
                "target": 15,
                "size": 3,
                "known_grid": [
                    [8, None, None],
                    [None, 5, None],
                    [None, None, 2],
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("solution", body)
        self.assertIn("grid_rows", body)
        self.assertIn("grid_text", body)
        self.assertEqual(body["solution"][0][0], 8)
        self.assertEqual(body["solution"][1][1], 5)
        self.assertEqual(body["solution"][2][2], 2)
        self.assertEqual(len(body["grid_rows"]), 3)

    def test_solve_endpoint_with_trace_includes_trace(self) -> None:
        response = self.client.post(
            "/solve",
            json={
                "target": 15,
                "size": 3,
                "trace": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("trace", body)
        self.assertTrue(len(body["trace"]) > 0)
        self.assertTrue(any("Select cell" in line for line in body["trace"]))

    def test_solve_endpoint_with_trace_steps_includes_walkthrough_frames(self) -> None:
        response = self.client.post(
            "/solve",
            json={
                "target": 15,
                "size": 3,
                "trace_steps": True,
                "trace_max_steps": 120,
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("trace_steps", body)
        self.assertTrue(len(body["trace_steps"]) > 0)
        first_step = body["trace_steps"][0]
        self.assertIn("event", first_step)
        self.assertIn("message", first_step)
        self.assertIn("grid", first_step)

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

    def test_solve_endpoint_supports_bounded_game_mode(self) -> None:
        response = self.client.post(
            "/solve",
            json={
                "target": 15,
                "size": 3,
                "game_mode": "bounded_by_size_squared",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(all(value <= 9 for row in body["solution"] for value in row))

    def test_count_endpoint_returns_exact_count(self) -> None:
        response = self.client.post(
            "/count",
            json={
                "target": 15,
                "size": 3,
                "mode": "exact",
                "max_seconds": 5.0,
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["exact"])
        self.assertEqual(body["count"], 8)

    def test_count_endpoint_auto_returns_estimate_fields(self) -> None:
        response = self.client.post(
            "/count",
            json={
                "target": 15,
                "size": 3,
                "mode": "auto",
                "max_seconds": 0.0,
                "sample_paths": 60,
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("mode_used", body)
        self.assertIn("estimated_count", body)

    def test_count_job_flow_completes_and_exposes_elapsed_time(self) -> None:
        start_response = self.client.post(
            "/count/jobs/start",
            json={
                "target": 15,
                "size": 3,
                "mode": "exact",
                "max_seconds": 5.0,
            },
        )
        self.assertEqual(start_response.status_code, 202)
        job_id = start_response.json()["job_id"]

        status_data = self._poll_job(job_id)
        self.assertEqual(status_data["status"], "completed")
        self.assertIn("elapsed_seconds", status_data)
        self.assertTrue(status_data["elapsed_seconds"] >= 0)
        self.assertIn("nodes_visited", status_data)
        self.assertTrue(status_data["nodes_visited"] >= 0)
        self.assertTrue(status_data["exact"])

    def test_count_job_can_be_canceled(self) -> None:
        start_response = self.client.post(
            "/count/jobs/start",
            json={
                "target": 34,
                "size": 4,
                "mode": "exact",
                "max_seconds": None,
            },
        )
        self.assertEqual(start_response.status_code, 202)
        job_id = start_response.json()["job_id"]

        cancel_response = self.client.post(f"/count/jobs/{job_id}/cancel")
        self.assertEqual(cancel_response.status_code, 200)

        status_data = self._poll_job(job_id)
        self.assertIn(status_data["status"], {"canceled", "completed"})
        self.assertIn("lower_bound", status_data)

    def _poll_job(self, job_id: str, timeout_seconds: float = 10.0) -> dict:
        deadline = time.time() + timeout_seconds
        last_status = {}
        while time.time() < deadline:
            status_response = self.client.get(f"/count/jobs/{job_id}")
            self.assertEqual(status_response.status_code, 200)
            last_status = status_response.json()
            if last_status["status"] in {"completed", "canceled", "failed"}:
                return last_status
            time.sleep(0.05)
        self.fail(f"Timed out waiting for job {job_id} to finish. Last status: {last_status}")


if __name__ == "__main__":
    unittest.main()
