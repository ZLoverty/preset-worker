"""Generate a local 3MF/Preset consistency report without Feishu access."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from preset_worker.slicers.contracts import Artifact, ProcessingContext
from preset_worker.three_mf import (
    validate_bambu_consistency,
    validate_creality_consistency,
    validate_elegoo_consistency,
    validate_orca_consistency,
    validate_prusa_slicer_consistency,
    validate_snapmaker_orca_consistency,
)
from preset_worker.three_mf.consistency import validate_flash_studio_consistency


VALIDATORS = {
    "BambuStudio": validate_bambu_consistency,
    "CrealityPrint": validate_creality_consistency,
    "ElegooSlicer": validate_elegoo_consistency,
    "FlashStudio": validate_flash_studio_consistency,
    "OrcaSlicer": validate_orca_consistency,
    "PrusaSlicer": validate_prusa_slicer_consistency,
    "SnapmakerOrcaSlicer": validate_snapmaker_orca_consistency,
}


def _artifact(path: Path, media_type: str | None = None) -> Artifact:
    if not path.is_file():
        raise FileNotFoundError(path)
    return Artifact(path.read_bytes(), path.name, media_type)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a local p9b2.consistency.v1 report from a Preset and 3MF."
    )
    parser.add_argument("--preset", required=True, type=Path, help="Preset JSON/INI path")
    parser.add_argument("--project", required=True, type=Path, help="3MF project path")
    parser.add_argument(
        "--slicer",
        choices=sorted(VALIDATORS),
        default="SnapmakerOrcaSlicer",
        help="Native slicer identity (default: SnapmakerOrcaSlicer)",
    )
    parser.add_argument("--output", type=Path, help="Write JSON to this path instead of stdout")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON")
    parser.add_argument("--pi-code", default="", help="Optional processing context PI code")
    parser.add_argument("--printer", default="", help="Optional processing context printer")
    parser.add_argument("--method-version", default="", help="Optional processing method version")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        preset = _artifact(args.preset, "application/json" if args.preset.suffix.lower() == ".json" else None)
        project = _artifact(args.project, "model/3mf")
        context = ProcessingContext(args.pi_code, args.printer, args.slicer, args.method_version)
        report = VALIDATORS[args.slicer](preset, project, context=context)
        text = json.dumps(
            report,
            ensure_ascii=False,
            indent=None if args.compact else 2,
            sort_keys=False,
        )
        if args.output:
            args.output.write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0
    except Exception as exc:
        print(f"consistency report failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
