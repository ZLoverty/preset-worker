"""Compare the ``preset data`` attachments in two Feishu Bitable tables.

The source table is configured with ``app_token_diff`` and
``table_id_diff``.  The target table uses ``FEISHU_APP_TOKEN`` and
``FEISHU_TABLE_ID``.  Authentication uses ``app_id_diff`` and
``app_secret_diff``.  Records are matched by normalized ``PI Code`` and
``Printer`` values.  This command is read-only against Feishu.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


AUTH_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
BITABLE_API = "https://open.feishu.cn/open-apis/bitable/v1"
MEDIA_URL = "https://open.feishu.cn/open-apis/drive/v1/medias/{}/download"
PAGE_SIZE = 100
DATA_NOT_READY_CODE = 1254607
MAX_DATA_NOT_READY_RETRIES = 5
SOURCE_APP_ENV = "app_token_diff"
SOURCE_TABLE_ENV = "table_id_diff"
TARGET_APP_ENV = "FEISHU_APP_TOKEN"
TARGET_TABLE_ENV = "FEISHU_TABLE_ID"
APP_ID_ENV = "app_id_diff"
APP_SECRET_ENV = "app_secret_diff"
PI_FIELDS = ("PI Code", "pi_code", "pi code", "PI code")
PRINTER_FIELDS = ("Printer", "printer")
PRESET_FIELDS = ("preset data", "preset_data")
METADATA_KEYS = {
    "from", "name", "type", "include", "version", "inherits", "setting_id",
    "description", "instantiation", "pm_method_version",
}


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def api_json(
    url: str,
    token: str | None = None,
    payload: dict | None = None,
    retry_count: int = 0,
) -> dict:
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers=headers,
        method="POST" if payload is not None else "GET",
    )
    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        try:
            error_code = json.loads(detail).get("code")
        except (TypeError, json.JSONDecodeError):
            error_code = None
        if error_code == DATA_NOT_READY_CODE and retry_count < MAX_DATA_NOT_READY_RETRIES:
            delay = min(2**retry_count, 8)
            print(
                f"[重试] 飞书数据尚未就绪，{delay} 秒后重试 "
                f"({retry_count + 1}/{MAX_DATA_NOT_READY_RETRIES})"
            )
            time.sleep(delay)
            return api_json(url, token, payload, retry_count + 1)
        raise RuntimeError(
            f"Feishu request failed: HTTP {exc.code}: {detail or exc.reason}"
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Feishu request failed: {exc}") from exc
    if result.get("code", 0) != 0:
        raise RuntimeError(f"Feishu API error {result.get('code')}: {result.get('msg')}")
    return result


class FeishuClient:
    def __init__(self, env: dict[str, str], verbose: bool = True) -> None:
        self.verbose = verbose
        missing = [key for key in (APP_ID_ENV, APP_SECRET_ENV) if not env.get(key)]
        if missing:
            raise RuntimeError(f"Missing .env values: {', '.join(missing)}")
        auth = api_json(
            AUTH_URL,
            payload={"app_id": env[APP_ID_ENV], "app_secret": env[APP_SECRET_ENV]},
        )
        self.token = auth["tenant_access_token"]

    def records(self, app_token: str, table_id: str) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        page_token = ""
        page = 0
        while True:
            page += 1
            query = {"page_size": str(PAGE_SIZE)}
            if page_token:
                query["page_token"] = page_token
            url = f"{BITABLE_API}/apps/{app_token}/tables/{table_id}/records?{urlencode(query)}"
            data = api_json(url, self.token).get("data", {})
            records.extend(data.get("items", []))
            if self.verbose:
                print(f"[进度] 读取表 {table_id}: 第 {page} 页，累计 {len(records)} 条")
            if not data.get("has_more"):
                return records
            page_token = data.get("page_token", "")
            if not page_token:
                raise RuntimeError("Feishu pagination response has no page_token")

    def download_attachment(self, attachment: dict[str, Any]) -> bytes:
        url = attachment_url(attachment)
        if not url:
            raise RuntimeError("attachment has no download URL or file token")
        request = Request(url, headers={"Authorization": f"Bearer {self.token}"})
        try:
            with urlopen(request, timeout=120) as response:
                return response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Download failed HTTP {exc.code}: {detail or exc.reason}") from exc
        except (URLError, TimeoutError) as exc:
            raise RuntimeError(f"Download failed: {exc}") from exc


def text_cell(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value).strip()
    if isinstance(value, list):
        return " ".join(text_cell(item) for item in value).strip()
    if isinstance(value, dict):
        return str(value.get("text") or value.get("name") or value.get("value") or "").strip()
    return ""


def field_value(fields: dict[str, Any], names: tuple[str, ...]) -> object:
    for name in names:
        if name in fields:
            return fields[name]
    return ""


def normalize_identity(value: object) -> str:
    """Normalize case, Unicode variants, whitespace and separators for identity matching."""
    text = unicodedata.normalize("NFKC", text_cell(value)).casefold()
    return "".join(char for char in text if char.isalnum())


def normalize_printer(value: object) -> str:
    """Normalize printer names, including the BBL/Bambu naming variant."""
    normalized = normalize_identity(value)
    if normalized.startswith("bbl"):
        normalized = "bambu" + normalized[3:]
    # Anycubic uses both "Anycubic Kobra S1" and "Anycubic S1" for
    # the same printer in different records.
    if normalized == "anycubickobras1":
        return "anycubics1"
    return normalized


def record_key(fields: dict[str, Any]) -> tuple[str, str] | None:
    pi_code = text_cell(field_value(fields, PI_FIELDS))
    printer = text_cell(field_value(fields, PRINTER_FIELDS))
    normalized = (normalize_identity(pi_code), normalize_printer(printer))
    return normalized if all(normalized) else None


def attachment_list(value: object) -> list[dict[str, Any]]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def attachment_url(attachment: dict[str, Any]) -> str | None:
    """Use Feishu's signed attachment URL when present, with token fallback."""
    direct_url = attachment.get("url") or attachment.get("tmp_url")
    if direct_url:
        return str(direct_url)
    token = (
        attachment.get("attachmentToken")
        or attachment.get("file_token")
        or attachment.get("token")
    )
    return MEDIA_URL.format(token) if token else None


def attachment_fingerprints(
    value: object,
    download: Callable[[dict[str, Any]], bytes],
    progress: Callable[[str], None] | None = None,
    label: str = "附件",
) -> tuple[list[dict[str, Any]], list[str]]:
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, attachment in enumerate(attachment_list(value), start=1):
        name = str(attachment.get("name") or f"attachment_{index}")
        started = time.perf_counter()
        if progress:
            progress(f"下载 {label} {name}")
        try:
            content = download(attachment)
        except Exception as exc:  # report one bad attachment without hiding other differences
            errors.append(f"{name}: {exc}")
            if progress:
                progress(f"下载失败 {label} {name} ({time.perf_counter() - started:.1f}s): {exc}")
            continue
        if progress:
            progress(f"下载完成 {label} {name} ({len(content) / 1024:.0f}KB, {time.perf_counter() - started:.1f}s)")
        results.append(
            {
                "name": name,
                "normalized_name": normalize_identity(name),
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "_content": content,
            }
        )
    return results, errors


def compare_attachment_lists(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> str:
    left_content = collections.Counter(item["sha256"] for item in left)
    right_content = collections.Counter(item["sha256"] for item in right)
    if left_content != right_content:
        return "different"
    left_names = collections.Counter(item["normalized_name"] for item in left)
    right_names = collections.Counter(item["normalized_name"] for item in right)
    return "same" if left_names == right_names else "same_content_different_name"


def overlap_differences(left: object, right: object, path: str = "$") -> list[dict[str, Any]]:
    """Compare shared preset parameters while ignoring target-only fields."""
    if isinstance(left, dict) and isinstance(right, dict):
        differences: list[dict[str, Any]] = []
        for key in sorted(set(left) & set(right)):
            if path == "$" and key in METADATA_KEYS:
                continue
            differences.extend(overlap_differences(left[key], right[key], f"{path}.{key}"))
        return differences
    if isinstance(left, list) and isinstance(right, list):
        differences: list[dict[str, Any]] = []
        for index in range(min(len(left), len(right))):
            differences.extend(overlap_differences(left[index], right[index], f"{path}[{index}]"))
        return differences
    if left != right:
        return [{"path": path, "source": left, "target": right}]
    return []


def compare_preset_attachments(
    source: list[dict[str, Any]], target: list[dict[str, Any]]
) -> tuple[str, list[dict[str, Any]]]:
    if len(source) != len(target):
        return "attachment_count_different", []
    all_differences: list[dict[str, Any]] = []
    for index, (source_item, target_item) in enumerate(zip(source, target), start=1):
        try:
            source_data = json.loads(source_item["_content"].decode("utf-8"))
            target_data = json.loads(target_item["_content"].decode("utf-8"))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
            return "unparseable", []
        differences = overlap_differences(source_data, target_data)
        for difference in differences:
            difference["attachment_index"] = index
        all_differences.extend(differences)
    return ("parameter_different" if all_differences else "same_parameters"), all_differences


def report_attachment(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if key != "_content"}


def index_records(records: list[dict[str, Any]]) -> tuple[dict[tuple[str, str], dict[str, Any]], list[dict[str, Any]]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    invalid: list[dict[str, Any]] = []
    for record in records:
        fields = record.get("fields", {})
        key = record_key(fields)
        if key is None:
            invalid.append({"record_id": record.get("record_id", ""), "reason": "missing PI Code or Printer"})
            continue
        if key in indexed:
            invalid.append({"record_id": record.get("record_id", ""), "key": list(key), "reason": "duplicate identity"})
            continue
        indexed[key] = record
    return indexed, invalid


def compare_tables(
    source_records: list[dict[str, Any]],
    target_records: list[dict[str, Any]],
    download: Callable[[dict[str, Any]], bytes],
    selected_keys: set[tuple[str, str]] | None = None,
    limit: int | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    source, source_invalid = index_records(source_records)
    target, target_invalid = index_records(target_records)
    keys = sorted(set(source) | set(target))
    if selected_keys is not None:
        keys = [key for key in keys if key in selected_keys]
    if limit is not None:
        keys = keys[:limit]

    results: list[dict[str, Any]] = []
    for index, key in enumerate(keys, start=1):
        if progress:
            progress(f"比较记录 {index}/{len(keys)}: {'::'.join(key)}")
        left = source.get(key)
        right = target.get(key)
        item: dict[str, Any] = {"key": "::".join(key), "pi_code": key[0], "printer": key[1]}
        if left is None or right is None:
            item["status"] = "source_only" if right is None else "target_only"
            item["source_record_id"] = (left or {}).get("record_id")
            item["target_record_id"] = (right or {}).get("record_id")
            results.append(item)
            if progress:
                progress(f"比较结果 {item['key']}: {item['status']}")
            continue
        source_value = field_value(left.get("fields", {}), PRESET_FIELDS)
        target_value = field_value(right.get("fields", {}), PRESET_FIELDS)
        source_files, source_errors = attachment_fingerprints(
            source_value, download, progress, f"源表 {item['key']}"
        )
        target_files, target_errors = attachment_fingerprints(
            target_value, download, progress, f"目标表 {item['key']}"
        )
        item.update(
            {
                "source_record_id": left.get("record_id"),
                "target_record_id": right.get("record_id"),
                "source_attachments": [report_attachment(item) for item in source_files],
                "target_attachments": [report_attachment(item) for item in target_files],
            }
        )
        errors = {"source": source_errors, "target": target_errors}
        if source_errors or target_errors:
            item["status"] = "download_error"
            item["errors"] = errors
        else:
            item["status"], item["parameter_differences"] = compare_preset_attachments(
                source_files, target_files
            )
        results.append(item)
        if progress:
            difference_count = len(item.get("parameter_differences", []))
            progress(
                f"比较结果 {item['key']}: {item['status']}"
                + (f"，参数差异 {difference_count} 项" if difference_count else "")
            )
    return {"results": results, "invalid_source": source_invalid, "invalid_target": target_invalid}


def _mapping_record(record: dict[str, Any]) -> dict[str, Any]:
    fields = record.get("fields", {})
    return {
        "record_id": record.get("record_id", ""),
        "pi_code": text_cell(field_value(fields, PI_FIELDS)),
        "printer": text_cell(field_value(fields, PRINTER_FIELDS)),
        "preset_data": attachment_list(field_value(fields, PRESET_FIELDS)),
    }


def build_identity_mapping(
    source_records: list[dict[str, Any]],
    target_records: list[dict[str, Any]],
    selected_keys: set[tuple[str, str]] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    source, source_invalid = index_records(source_records)
    target, target_invalid = index_records(target_records)
    keys = sorted(set(source) | set(target))
    if selected_keys is not None:
        keys = [key for key in keys if key in selected_keys]
    if limit is not None:
        keys = keys[:limit]
    return {
        "entries": [
            {
                "key": "::".join(key),
                "source": _mapping_record(source[key]) if key in source else None,
                "target": _mapping_record(target[key]) if key in target else None,
            }
            for key in keys
        ],
        "invalid_source": source_invalid,
        "invalid_target": target_invalid,
    }


def mapping_records(mapping: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_records: list[dict[str, Any]] = []
    target_records: list[dict[str, Any]] = []
    for entry in mapping.get("entries", []):
        for side, records in (("source", source_records), ("target", target_records)):
            item = entry.get(side)
            if item is None:
                continue
            records.append(
                {
                    "record_id": item.get("record_id", ""),
                    "fields": {
                        "PI Code": item.get("pi_code", ""),
                        "Printer": item.get("printer", ""),
                        "preset data": item.get("preset_data", []),
                    },
                }
            )
    return source_records, target_records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument("--key", action="append", help="Only compare a normalized PI Code::Printer key")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path, help="Write the JSON report to this path")
    parser.add_argument("--mapping", type=Path, default=Path("comparison-mapping.json"), help="Identity mapping file")
    parser.add_argument("--refresh-mapping", action="store_true", help="Re-read both tables and rebuild the mapping")
    parser.add_argument("--dry-run", action="store_true", help="Accepted for consistency; this command is always read-only")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress logs")
    args = parser.parse_args(argv)

    try:
        env = load_env(args.env)
        required = (SOURCE_APP_ENV, SOURCE_TABLE_ENV, TARGET_APP_ENV, TARGET_TABLE_ENV)
        missing = [key for key in required if not env.get(key)]
        if missing:
            raise RuntimeError(f"Missing .env values: {', '.join(missing)}")
        progress = (lambda message: print(f"[进度] {message}")) if not args.quiet else None
        if progress:
            progress("开始鉴权")
        client = FeishuClient(env, verbose=not args.quiet)
        if progress:
            progress("鉴权完成，开始读取源表")
        try:
            source_records = client.records(env[SOURCE_APP_ENV], env[SOURCE_TABLE_ENV])
        except RuntimeError as exc:
            raise RuntimeError(
                f"读取源表失败 ({SOURCE_APP_ENV}/{SOURCE_TABLE_ENV}): {exc}"
            ) from exc
        try:
            target_records = client.records(env[TARGET_APP_ENV], env[TARGET_TABLE_ENV])
        except RuntimeError as exc:
            raise RuntimeError(
                f"读取目标表失败 ({TARGET_APP_ENV}/{TARGET_TABLE_ENV}): {exc}"
            ) from exc
        selected = None
        if args.key:
            selected = set()
            for value in args.key:
                parts = value.split("::", 1)
                if len(parts) != 2:
                    raise RuntimeError(f"Invalid --key value: {value!r}; expected PI Code::Printer")
                selected.add((normalize_identity(parts[0]), normalize_printer(parts[1])))
        if progress:
            progress(f"两张表读取完成：源表 {len(source_records)} 条，目标表 {len(target_records)} 条")
        if args.mapping.exists() and not args.refresh_mapping:
            if progress:
                progress(f"复用身份映射：{args.mapping}")
            mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
        else:
            mapping = build_identity_mapping(source_records, target_records, selected, args.limit)
            mapping["source_config"] = {"app": env[SOURCE_APP_ENV], "table": env[SOURCE_TABLE_ENV]}
            mapping["target_config"] = {"app": env[TARGET_APP_ENV], "table": env[TARGET_TABLE_ENV]}
            args.mapping.parent.mkdir(parents=True, exist_ok=True)
            args.mapping.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
            if progress:
                progress(f"身份映射已保存：{args.mapping}，共 {len(mapping.get('entries', []))} 个身份")
        source_records, target_records = mapping_records(mapping)
        report = compare_tables(
            source_records,
            target_records,
            client.download_attachment,
            selected,
            args.limit,
            progress,
        )
        report["invalid_source"] = mapping.get("invalid_source", [])
        report["invalid_target"] = mapping.get("invalid_target", [])
        if args.output:
            if progress:
                progress(f"写入报告：{args.output}")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        counts = collections.Counter(item["status"] for item in report["results"])
        print(json.dumps({"counts": counts, "invalid_source": len(report["invalid_source"]), "invalid_target": len(report["invalid_target"]), "output": str(args.output) if args.output else None}, ensure_ascii=False, indent=2, default=dict))
        for item in report["results"]:
            print(f"{item['status']:28} {item['key']}")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
