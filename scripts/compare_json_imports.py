"""Find JSON filenames present in a source tree but missing from a target tree."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def collect_json_files(root: Path) -> dict[str, str]:
    """Return filename keys and their original spelling under *root*."""
    return {
        path.name.casefold(): path.name
        for path in root.rglob("*.json")
        if path.is_file()
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find source JSON filenames that are missing from the target path."
    )
    parser.add_argument("source", type=Path, help="Source directory containing JSON files")
    parser.add_argument("target", type=Path, help="Target directory containing imported JSON files")
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

    source_files = collect_json_files(source)
    target_files = collect_json_files(target)
    missing = sorted(
        source_files[name]
        for name in source_files.keys() - target_files.keys()
    )
    result = {
        "source": str(source),
        "target": str(target),
        "source_json_count": len(source_files),
        "target_json_count": len(target_files),
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
