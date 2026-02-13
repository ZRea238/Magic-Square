import json
import tempfile
import unittest
from pathlib import Path

from main import load_puzzle_from_file, run


class TestMainJsonInput(unittest.TestCase):
    def test_loads_valid_payload_with_known_grid(self) -> None:
        payload = {
            "target": 9,
            "size": 3,
            "known_grid": [[None, 3, None], [3, None, None], [None, None, None]],
        }
        file_path = self._write_json(payload)

        target, size, known_grid = load_puzzle_from_file(file_path)

        self.assertEqual(target, 9)
        self.assertEqual(size, 3)
        self.assertEqual(known_grid, payload["known_grid"])

    def test_loads_valid_payload_without_known_grid(self) -> None:
        payload = {
            "target": 6,
            "size": 2,
        }
        file_path = self._write_json(payload)

        target, size, known_grid = load_puzzle_from_file(file_path)

        self.assertEqual(target, 6)
        self.assertEqual(size, 2)
        self.assertIsNone(known_grid)

    def test_raises_when_json_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bad_path = Path(temp_dir) / "bad.json"
            bad_path.write_text("{ not valid json", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_puzzle_from_file(str(bad_path))

    def test_raises_when_required_fields_are_missing(self) -> None:
        file_path = self._write_json({"size": 2})
        with self.assertRaises(ValueError):
            load_puzzle_from_file(file_path)

    def test_loaded_payload_can_be_solved(self) -> None:
        payload = {
            "target": 6,
            "size": 2,
            "known_grid": [[None, None], [None, None]],
        }
        file_path = self._write_json(payload)
        target, size, known_grid = load_puzzle_from_file(file_path)

        solution = run(target=target, size=size, known_grid=known_grid)
        self.assertEqual(solution, [[3, 3], [3, 3]])

    def _write_json(self, payload: dict) -> str:
        tmp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        tmp_file.write(json.dumps(payload))
        tmp_file.flush()
        tmp_file.close()
        self.addCleanup(lambda: Path(tmp_file.name).unlink(missing_ok=True))
        return tmp_file.name


if __name__ == "__main__":
    unittest.main()
