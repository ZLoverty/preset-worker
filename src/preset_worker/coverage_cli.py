"""CLI for CoverageTarget synchronization."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .services.coverage_sync import CoverageTableConfig, synchronize
from .services.enrichment import FeishuClient, load_env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="coverage-sync")
    parser.add_argument("--env", type=Path, default=Path(".env"))
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        env = load_env(args.env)
        config = CoverageTableConfig.from_env(env)
        result = synchronize(FeishuClient(env), config, dry_run=args.dry_run)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("validation_errors") else 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
