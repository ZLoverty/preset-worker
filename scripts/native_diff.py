"""Generate a local native Preset diff without Feishu access."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from preset_worker.diff import serialize_unified_diff
from preset_worker.slicers.contracts import Artifact, ProcessingContext
from preset_worker.slicers.registry import default_processor_registry


def _artifact(path: Path) -> Artifact:
    if not path.is_file():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    media_type = "application/json" if suffix == ".json" else "text/plain"
    return Artifact(path.read_bytes(), path.name, media_type)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the native UnifiedDiff JSON for two Preset artifacts."
    )
    parser.add_argument(
        "--candidate",
        required=True,
        type=Path,
        help="New/candidate Preset JSON or INI path",
    )
    parser.add_argument(
        "--base",
        type=Path,
        help="Existing/base Preset JSON or INI path; omit for CREATE diff",
    )
    parser.add_argument(
        "--slicer",
        default="SnapmakerOrcaSlicer",
        help="Native slicer identity (default: SnapmakerOrcaSlicer)",
    )
    parser.add_argument("--output", type=Path, help="Write JSON to this path instead of stdout")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON")
    parser.add_argument("--pi-code", default="PI", help="Processing context PI code")
    parser.add_argument("--printer", default="Printer", help="Processing context printer")
    parser.add_argument("--method-version", default="local", help="Processing method version")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        registry = default_processor_registry()
        processor = registry.get(args.slicer)
        if processor is None:
            raise ValueError(f"unsupported slicer: {args.slicer}")
        context = ProcessingContext(args.pi_code, args.printer, args.slicer, args.method_version)
        base = _artifact(args.base) if args.base else None
        candidate = _artifact(args.candidate)
        diff = processor.diff(base, candidate, context)
        text = serialize_unified_diff(diff)
        if not args.compact:
            text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
        if args.output:
            args.output.write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0
    except Exception as exc:
        print(f"native diff failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
