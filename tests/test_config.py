import tempfile
import unittest
from pathlib import Path

from preset_worker.config import load_runtime_config


class RuntimeConfigTests(unittest.TestCase):
    def test_runtime_defaults_and_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "PRESET_WORKER_POLL_INTERVAL=3.5\nPRESET_WORKER_BATCH_SIZE=7\n",
                encoding="utf-8",
            )
            config = load_runtime_config(path)
        self.assertEqual(config.poll_interval, 3.5)
        self.assertEqual(config.batch_size, 7)

    def test_invalid_runtime_config_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("PRESET_WORKER_BATCH_SIZE=0\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_runtime_config(path)


if __name__ == "__main__":
    unittest.main()
