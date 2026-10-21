from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..slicers.contracts import Artifact
from .bambu_parser import parse_bambu_3mf, resolve_bambu_project
from .models import ResolutionContext


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m preset_worker.three_mf.diagnostics")
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect")
    inspect.add_argument("path", type=Path)
    inspect.add_argument("--output", type=Path)
    inspect.add_argument("--filament-slot", type=int)
    inspect.add_argument("--plate", type=int)
    args = parser.parse_args(argv)
    if args.command == "inspect":
        data = args.path.read_bytes()
        snapshot = parse_bambu_3mf(Artifact(data, args.path.name, "model/3mf"))
        resolved = resolve_bambu_project(snapshot, ResolutionContext(args.filament_slot, args.plate))
        report = {"snapshot": snapshot.as_dict(), "resolved": resolved.as_dict()}
        output = json.dumps(report, ensure_ascii=False, indent=2, default=str)
        if args.output:
            args.output.write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
