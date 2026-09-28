"""Thin command-line interface for manual Submission operations."""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
from pathlib import Path
from typing import Callable

from .services.enrichment import SubmissionEnrichment
from .services.enrichment_api import enrich_submission
from .services.publication_api import publish_submission
from .config import build_feishu_client, load_runtime_config
from .runtime import WorkerRuntime


def _result_dict(result: object) -> dict:
    return result.__dict__ if hasattr(result, "__dict__") else {"result": result}


def main(
    argv: list[str] | None = None,
    *,
    enrich_service: Callable[[str], object] | None = None,
    publish_service: Callable[[str], object] | None = None,
    runtime_factory: Callable[[Path], WorkerRuntime] | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="preset-worker")
    parser.add_argument("--env", type=Path, default=Path(".env"), help=".env 文件路径")
    commands = parser.add_subparsers(dest="command", required=True)
    enrich_parser = commands.add_parser("enrich", help="enrich one Submission")
    enrich_parser.add_argument("submission_id")
    backfill_parser = commands.add_parser(
        "backfill-base-version-no-text",
        help="repair historical Submission base version display snapshots",
    )
    backfill_parser.add_argument("--limit", type=int, help="最多修复多少条")
    publish_parser = commands.add_parser("publish", help="publish one APPROVING Submission")
    publish_parser.add_argument("submission_id")
    commands.add_parser("run", help="run the polling Worker")
    commands.add_parser("run-once", help="process one polling cycle")
    args = parser.parse_args(argv)

    try:
        if args.command == "enrich":
            service = enrich_service or (lambda submission_id: enrich_submission(submission_id, env_path=args.env))
            result = service(args.submission_id)
            print(json.dumps(_result_dict(result), ensure_ascii=False, indent=2, default=str))
            return 0
        elif args.command == "backfill-base-version-no-text":
            client = build_feishu_client(args.env)
            result = SubmissionEnrichment(client).backfill_base_version_no_text(limit=args.limit)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        elif args.command == "publish":
            service = publish_service or (lambda submission_id: publish_submission(submission_id, env_path=args.env))
            result = service(args.submission_id)
            print(json.dumps(_result_dict(result), ensure_ascii=False, indent=2, default=str))
            return 0
        else:
            config = load_runtime_config(args.env)
            runtime = (
                runtime_factory(args.env)
                if runtime_factory
                else WorkerRuntime(
                    build_feishu_client(args.env),
                    batch_size=config.batch_size,
                    poll_interval=config.poll_interval,
                )
            )
            if args.command == "run-once":
                runtime.run_once()
                return 0
            logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
            previous_handlers = {}

            def request_stop(signum, _frame):
                logging.getLogger(__name__).info("termination signal received signal=%s", signum)
                runtime.request_stop()

            for signum in (signal.SIGINT, getattr(signal, "SIGTERM", None)):
                if signum is not None:
                    previous_handlers[signum] = signal.getsignal(signum)
                    signal.signal(signum, request_stop)
            try:
                runtime.run()
            finally:
                for signum, handler in previous_handlers.items():
                    signal.signal(signum, handler)
            return 0
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
