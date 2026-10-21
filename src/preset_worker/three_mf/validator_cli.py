from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..slicers.contracts import Artifact
from .consistency import validate_bambu_consistency


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m preset_worker.three_mf.validator_cli")
    sub = parser.add_subparsers(dest="command", required=True)
    compare = sub.add_parser("compare")
    compare.add_argument("preset", type=Path)
    compare.add_argument("project", type=Path)
    compare.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.command == "compare":
        report = validate_bambu_consistency(
            Artifact(args.preset.read_bytes(), args.preset.name, "application/json"),
            Artifact(args.project.read_bytes(), args.project.name, "model/3mf"),
        )
        text = json.dumps(report, ensure_ascii=False, indent=2, default=str)
        if args.output:
            args.output.write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
