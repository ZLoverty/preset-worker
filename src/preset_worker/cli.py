"""Thin command-line interface for manual Submission operations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable

from .services.enrichment_api import enrich_submission
from .services.publication_api import publish_submission


def _result_dict(result: object) -> dict:
    return result.__dict__ if hasattr(result, "__dict__") else {"result": result}


def main(
    argv: list[str] | None = None,
    *,
    enrich_service: Callable[[str], object] | None = None,
    publish_service: Callable[[str], object] | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="preset-worker")
    parser.add_argument("--env", type=Path, default=Path(".env"), help=".env 文件路径")
    commands = parser.add_subparsers(dest="command", required=True)
    enrich_parser = commands.add_parser("enrich", help="enrich one Submission")
    enrich_parser.add_argument("submission_id")
    publish_parser = commands.add_parser("publish", help="publish one APPROVING Submission")
    publish_parser.add_argument("submission_id")
    args = parser.parse_args(argv)

    try:
        if args.command == "enrich":
            service = enrich_service or (lambda submission_id: enrich_submission(submission_id, env_path=args.env))
            result = service(args.submission_id)
        else:
            service = publish_service or (lambda submission_id: publish_submission(submission_id, env_path=args.env))
            result = service(args.submission_id)
        print(json.dumps(_result_dict(result), ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
