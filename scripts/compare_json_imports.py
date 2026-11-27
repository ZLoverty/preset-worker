"""Find preset filenames present in a source tree but missing from a target tree."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FORMAT_EXTENSIONS = {
    "json": (".json",),
    "ini": (".ini",),
    "auto": (".json", ".ini"),
}


def collect_preset_files(root: Path, file_format: str) -> dict[str, str]:
    """Return preset filename keys and their original spelling under *root*."""
    extensions = FORMAT_EXTENSIONS[file_format]
    return {
        path.name.casefold(): path.name
        for extension in extensions
        for path in root.rglob(f"*{extension}")
        if path.is_file()
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find source preset filenames missing from the target path."
    )
    parser.add_argument("source", type=Path, help="Source directory containing preset files")
    parser.add_argument("target", type=Path, help="Target directory containing imported preset files")
    parser.add_argument(
        "--format",
        choices=sorted(FORMAT_EXTENSIONS),
        default="auto",
        help="Preset file format to compare (default: auto, supports JSON and INI)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON file for the comparison result",
    )
    args = parser.parse_args()

    source = args.source.resolve()
    target = args.target.resolve()
    if not source.is_dir():
        parser.error(f"Source directory does not exist: {source}")
    if not target.is_dir():
        parser.error(f"Target directory does not exist: {target}")

    source_files = collect_preset_files(source, args.format)
    target_files = collect_preset_files(target, args.format)
    missing = sorted(
        source_files[name]
        for name in source_files.keys() - target_files.keys()
    )
    result = {
        "source": str(source),
        "target": str(target),
        "source_preset_count": len(source_files),
        "target_preset_count": len(target_files),
        "missing_count": len(missing),
        "missing": missing,
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
