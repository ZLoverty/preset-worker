"""Historically backfill ``slicer_version`` in the Submission Bitable table.

The module contains the pure timestamp/tag selection logic as well as the
small network clients used by the command-line entry point.  It intentionally
does not touch preset artifacts or any field other than ``slicer_version``.
"""

from __future__ import annotations

import argparse
from http.client import IncompleteRead, RemoteDisconnected
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import build_feishu_client
from .services.enrichment import load_env

logger = logging.getLogger(__name__)
GITHUB_API = "https://api.github.com"
DEFAULT_REPOSITORIES = {
    "BambuStudio": "bambulab/BambuStudio",
    "OrcaSlicer": "SoftFever/OrcaSlicer",
    "OrcaSlicer (Snapmaker)": "Snapmaker/OrcaSlicer",
    "CrealityPrint": "CrealityOfficial/CrealityPrint",
    "ElegooSlicer": "Elegoo-3D/ElegooSlicer",
    "PrusaSlicer": "prusa3d/PrusaSlicer",
}
ALIASES = {
    "Bambu Studio": "BambuStudio",
    "Orca Slicer": "OrcaSlicer",
    "OrcaSlicer Snapmaker": "OrcaSlicer (Snapmaker)",
}
EMPTY = (None, "", [], {})


@dataclass(frozen=True)
class VersionTag:
    name: str
    timestamp: datetime
    source: str = "tag"
    prerelease: bool = False
    draft: bool = False


def parse_timestamp(value: Any) -> datetime:
    """Parse Bitable ISO-8601 or numeric seconds/milliseconds as UTC."""
    if isinstance(value, bool) or value is None or value == "":
        raise ValueError("timestamp is empty")
    if isinstance(value, (int, float)):
        number = float(value)
        if abs(number) > 100_000_000_000:
            number /= 1000
        return datetime.fromtimestamp(number, tz=timezone.utc)
    text = str(value).strip()
    if text.isdigit():
        return parse_timestamp(int(text))
    normalized = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_slicer(value: Any) -> str | None:
    if isinstance(value, list) and value:
        return normalize_slicer(value[0])
    if isinstance(value, dict):
        return normalize_slicer(value.get("text") or value.get("name") or value.get("value"))
    if not isinstance(value, str):
        return None
    name = value.strip()
    return ALIASES.get(name, name) if name else None


def normalize_version_tag(tag: str) -> str | None:
    """Remove only the conventional leading v; preserve other tag formats."""
    value = tag.strip()
    if not value or any(char.isspace() for char in value):
        return None
    if value[:1].lower() == "v" and len(value) > 1 and value[1].isdigit():
        return value[1:]
    return value


def select_latest_tag(tags: Iterable[VersionTag], cutoff: datetime) -> VersionTag | None:
    cutoff = parse_timestamp(cutoff)
    eligible = [
        tag for tag in tags
        if not tag.draft and not tag.prerelease and tag.timestamp <= cutoff
    ]
    if not eligible:
        return None
    eligible.sort(key=lambda tag: (tag.timestamp, tag.name), reverse=True)
    if len(eligible) > 1 and eligible[0].timestamp == eligible[1].timestamp:
        logger.warning("tags share timestamp=%s; selected deterministic tag=%s", eligible[0].timestamp, eligible[0].name)
    return eligible[0]


def _request_json(url: str, *, token: str | None = None, retries: int = 3) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "preset-worker-slicer-backfill",
        "Connection": "close",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urlopen(Request(url, headers=headers), timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
            return result
        except HTTPError as exc:
            last = exc
            retryable = (
                exc.code == 429
                or exc.code >= 500
                or (exc.code == 403 and exc.headers.get("X-RateLimit-Remaining") == "0")
            )
            retry_after = exc.headers.get("Retry-After")
            if exc.code == 403 and (
                exc.headers.get("X-RateLimit-Remaining") == "0"
                or "rate limit" in str(exc).lower()
            ):
                reset = exc.headers.get("X-RateLimit-Reset")
                suffix = f"; reset epoch={reset}" if reset else ""
                raise RuntimeError(
                    "GitHub API rate limit exceeded; configure a valid GITHUB_TOKEN "
                    f"(or wait for the reset){suffix}"
                ) from exc
        except (IncompleteRead, RemoteDisconnected, ConnectionResetError, URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last, retryable = exc, True
            retry_after = None
        if not retryable or attempt >= retries:
            break
        try:
            delay = float(retry_after) if retry_after else min(2 ** attempt, 8)
        except ValueError:
            delay = min(2 ** attempt, 8)
        time.sleep(min(delay, 30))
    raise RuntimeError(f"GitHub request failed: {url}: {last}") from last


class GitHubTags:
    def __init__(
        self,
        token: str | None = None,
        *,
        request: Callable[..., dict[str, Any]] = _request_json,
        cache_file: Path | None = None,
        cache_ttl_seconds: float = 24 * 60 * 60,
        refresh_cache: bool = False,
        refresh_repositories: Iterable[str] = (),
    ):
        self.token = token
        self.request = request
        self.cache: dict[str, list[VersionTag]] = {}
        self.errors: dict[str, Exception] = {}
        self.cache_file = cache_file
        self.cache_ttl_seconds = cache_ttl_seconds
        self.refresh_repositories = set(refresh_repositories)
        if cache_file and not refresh_cache:
            self._load_cache()

    def _load_cache(self) -> None:
        try:
            payload = json.loads(self.cache_file.read_text(encoding="utf-8"))
            repositories = payload.get("repositories", {})
            now = time.time()
            for repository, item in repositories.items():
                if repository in self.refresh_repositories:
                    logger.info("GitHub metadata cache bypass repository=%s", repository)
                    continue
                if not isinstance(item, dict) or now - float(item.get("fetched_at", 0)) > self.cache_ttl_seconds:
                    continue
                tags = []
                for raw in item.get("tags", []):
                    tags.append(VersionTag(
                        str(raw["name"]),
                        parse_timestamp(raw["timestamp"]),
                        str(raw.get("source", "tag")),
                        bool(raw.get("prerelease")),
                        bool(raw.get("draft")),
                    ))
                self.cache[str(repository)] = tags
                logger.info("GitHub metadata cache hit repository=%s versions=%d", repository, len(tags))
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            logger.warning("ignoring invalid GitHub metadata cache file=%s: %s", self.cache_file, exc)

    def _save_cache(self) -> None:
        if not self.cache_file:
            return
        payload = {
            "version": 1,
            "repositories": {
                repository: {
                    "fetched_at": time.time(),
                    "tags": [
                        {
                            "name": tag.name,
                            "timestamp": tag.timestamp.isoformat(),
                            "source": tag.source,
                            "prerelease": tag.prerelease,
                            "draft": tag.draft,
                        }
                        for tag in tags
                    ],
                }
                for repository, tags in self.cache.items()
            },
        }
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.cache_file.with_suffix(self.cache_file.suffix + ".tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.cache_file)
            logger.info("GitHub metadata cache saved file=%s", self.cache_file)
        except OSError as exc:
            logger.warning("could not save GitHub metadata cache file=%s: %s", self.cache_file, exc)

    def _pages(self, path: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for page in range(1, 101):
            # Release payloads can be large enough for GitHub/proxies to close
            # a chunked response mid-read. Smaller pages make retries cheap.
            query = urlencode({"per_page": 30, "page": page})
            data = self.request(f"{GITHUB_API}{path}?{query}", token=self.token)
            items = data if isinstance(data, list) else data.get("items", []) if isinstance(data, dict) else []
            if not items:
                break
            logger.info("GitHub metadata path=%s page=%d items=%d", path, page, len(items))
            result.extend(item for item in items if isinstance(item, dict))
            if len(items) < 30:
                break
        return result

    def tags(self, repository: str) -> list[VersionTag]:
        if repository in self.cache:
            return self.cache[repository]
        if repository in self.errors:
            raise self.errors[repository]
        logger.info("GitHub metadata loading repository=%s authenticated=%s", repository, bool(self.token))
        try:
            releases = self._pages(f"/repos/{repository}/releases")
            by_name: dict[str, VersionTag] = {}
            for release in releases:
                published = release.get("published_at")
                if release.get("tag_name") and published:
                    by_name[str(release["tag_name"])] = VersionTag(
                        str(release["tag_name"]), parse_timestamp(published), "release",
                        bool(release.get("prerelease")), bool(release.get("draft")),
                    )
            for tag in self._pages(f"/repos/{repository}/tags"):
                name, sha = tag.get("name"), (tag.get("commit") or {}).get("sha")
                if not name or not sha or name in by_name:
                    continue
                tag_data: dict[str, Any] | None = None
                try:
                    tag_data = self.request(f"{GITHUB_API}/repos/{repository}/git/tags/{sha}", token=self.token)
                except RuntimeError as exc:
                    if "rate limit exceeded" in str(exc):
                        raise
                    pass  # lightweight tag; use target commit below
                date = (tag_data or {}).get("tagger", {}).get("date")
                target_sha = ((tag_data or {}).get("object") or {}).get("sha", sha)
                if not date:
                    commit = self.request(f"{GITHUB_API}/repos/{repository}/commits/{target_sha}", token=self.token)
                    date = ((commit.get("commit") or {}).get("committer") or {}).get("date")
                if date:
                    by_name[str(name)] = VersionTag(str(name), parse_timestamp(date), "tag")
            self.cache[repository] = list(by_name.values())
            self._save_cache()
            logger.info("GitHub metadata loaded repository=%s versions=%d", repository, len(by_name))
            return self.cache[repository]
        except Exception as exc:
            self.errors[repository] = exc
            raise


def _field_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list) and value:
        return _field_text(value[0])
    if isinstance(value, dict):
        return _field_text(value.get("text") or value.get("name") or value.get("value"))
    return ""


def load_repositories(env: dict[str, str]) -> dict[str, str]:
    raw = env.get("SLICER_REPOSITORIES_JSON") or os.getenv("SLICER_REPOSITORIES_JSON")
    if not raw:
        return dict(DEFAULT_REPOSITORIES)
    custom = json.loads(raw)
    if not isinstance(custom, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in custom.items()):
        raise ValueError("SLICER_REPOSITORIES_JSON must be an object of slicer names to owner/repo")
    return custom


def run_backfill(client: Any, github: GitHubTags, repositories: dict[str, str], *, dry_run: bool = False, overwrite: bool = False, limit: int | None = None, slicer: str | None = None) -> dict[str, int]:
    summary: dict[str, int] = {name: 0 for name in ("UPDATED", "WOULD_UPDATE", "SKIPPED_EXISTING", "SKIPPED_UNKNOWN_SLICER", "SKIPPED_INVALID_DATE", "SKIPPED_NO_ELIGIBLE_TAG", "SKIPPED_AMBIGUOUS_TAG", "FAILED_READ", "FAILED_WRITE")}
    try:
        records = client.list_records(client.submission_table_id, limit=limit)
    except Exception:
        summary["FAILED_READ"] += 1
        logger.exception("failed to read Submission records")
        return summary
    processed = 0
    for record in records:
        fields = record.get("fields") or {}
        existing = _field_text(fields.get("slicer_version"))
        if existing and not overwrite:
            summary["SKIPPED_EXISTING"] += 1
            continue
        name = normalize_slicer(fields.get("slicer"))
        if slicer and name != slicer:
            continue
        repository = repositories.get(name or "")
        if not repository:
            summary["SKIPPED_UNKNOWN_SLICER"] += 1
            logger.warning("SKIPPED_UNKNOWN_SLICER record=%s slicer=%r", record.get("record_id"), name)
            continue
        try:
            cutoff = parse_timestamp(fields.get("created_at"))
        except ValueError:
            summary["SKIPPED_INVALID_DATE"] += 1
            logger.warning("SKIPPED_INVALID_DATE record=%s", record.get("record_id"))
            continue
        try:
            selected = select_latest_tag(github.tags(repository), cutoff)
        except Exception as exc:
            summary["FAILED_READ"] += 1
            # A repository-level failure is cached by GitHubTags. Keep normal
            # output concise instead of printing the same chained traceback
            # once per record; DEBUG still retains the diagnostic traceback.
            logger.error(
                "FAILED_READ record=%s repository=%s: %s",
                record.get("record_id"),
                repository,
                exc,
            )
            logger.debug("FAILED_READ traceback record=%s", record.get("record_id"), exc_info=True)
            continue
        if selected is None:
            summary["SKIPPED_NO_ELIGIBLE_TAG"] += 1
            continue
        version = normalize_version_tag(selected.name)
        if version is None:
            summary["SKIPPED_AMBIGUOUS_TAG"] += 1
            logger.warning("SKIPPED_AMBIGUOUS_TAG record=%s tag=%s", record.get("record_id"), selected.name)
            continue
        record_id = str(record.get("record_id") or record.get("id") or "")
        if dry_run:
            summary["WOULD_UPDATE"] += 1
            logger.info("WOULD_UPDATE record=%s %r -> %s (tag=%s)", record_id, existing, version, selected.name)
        else:
            try:
                current = client.get_record(client.submission_table_id, record_id)
                current_value = _field_text((current.get("fields") or {}).get("slicer_version"))
                if current_value and current_value != existing and not overwrite:
                    summary["SKIPPED_EXISTING"] += 1
                    continue
                client.update_submission(record_id, {"slicer_version": version})
                summary["UPDATED"] += 1
            except Exception:
                summary["FAILED_WRITE"] += 1
                logger.exception("FAILED_WRITE record=%s", record_id)
        processed += 1
        if limit and processed >= limit:
            break
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--slicer")
    parser.add_argument("--cache-file", type=Path, default=Path(".cache/slicer-version-github.json"))
    parser.add_argument("--cache-ttl-hours", type=float, default=24.0)
    parser.add_argument("--refresh-cache", action="store_true", help="ignore existing local GitHub metadata cache")
    parser.add_argument(
        "--refresh-repository",
        action="append",
        default=[],
        help="refresh one repository while preserving other cached repositories; repeatable",
    )
    parser.add_argument("--no-cache", action="store_true", help="disable reading and writing local GitHub metadata cache")
    parser.add_argument("--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s %(levelname)s %(message)s")
    try:
        env = load_env(args.env)
        logger.info("GitHub token configured=%s", bool(env.get("GITHUB_TOKEN") or env.get("GIT_ACCESS_TOKEN")))
        client = build_feishu_client(args.env)
        if args.cache_ttl_hours <= 0:
            raise ValueError("--cache-ttl-hours must be > 0")
        github = GitHubTags(
            env.get("GITHUB_TOKEN") or env.get("GIT_ACCESS_TOKEN"),
            cache_file=None if args.no_cache else args.cache_file,
            cache_ttl_seconds=args.cache_ttl_hours * 60 * 60,
            refresh_cache=args.refresh_cache,
            refresh_repositories=args.refresh_repository,
        )
        summary = run_backfill(client, github, load_repositories(env), dry_run=args.dry_run, overwrite=args.overwrite, limit=args.limit, slicer=args.slicer)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 1 if summary["FAILED_READ"] or summary["FAILED_WRITE"] else 0
    except Exception as exc:
        logger.error("backfill failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
