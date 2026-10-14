"""Run the slicer version backfill from a source checkout."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from preset_worker.backfill_slicer_version import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
