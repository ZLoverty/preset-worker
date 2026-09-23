"""Migrate selected fields from a legacy Bitable table to Submission.

The source Base/table is read from ``app_token`` and ``table_id`` in the
environment used by ``der_to_pst_migration.py``.  The destination is the
configured worker Submission table.  Only the explicitly listed fields are
copied; all other source columns are ignored.

Examples::

    python scripts/migrate_to_submission.py --dry-run
    python scripts/migrate_to_submission.py --record-id recxxx
    python scripts/migrate_to_submission.py --limit 50

Attachments are downloaded from the source and uploaded into the destination
Base one by one. The target record receives the newly returned file tokens.
Use ``--env`` to point at a migration-specific environment file.
"""

from __future__ import annotations

import argparse
import copy
import json
import mimetypes
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from preset_worker.services.enrichment import (
    AUTH_URL,
    BITABLE_API,
    UPLOAD_URL,
    _api_json,
    _attachment_url,
    load_env,
)


SOURCE_APP_ENV = "app_token"
SOURCE_TABLE_ENV = "table_id"
TARGET_APP_ENV = "FEISHU_APP_TOKEN"
TARGET_TABLE_ENV = "FEISHU_SUBMISSION_TABLE_ID"

SOURCE_PI_FIELDS = ("pi_code", "PI code", "PI Code")
SOURCE_PRINTER_FIELDS = ("printer", "Printer")
SOURCE_PROFILE_FIELDS = ("preset data", "preset_data")
PRINTER_VALUE_MAP = {
    "Bambu P2S": "BBL P2S",
    "Bambu A1": "BBL A1",
    "Bambu H2D": "BBL H2D",
    "Bambu H2S": "BBL H2S",
    "Bambu H2C": "BBL H2C",
    "Bambu X2D": "BBL X2D",
    "Bambu A2L": "BBL A2L",
    "Bambu P1S": "BBL P1S",
    "Prusa core one": "Prusa Core One",
    "Anycubic S1": "Anycubic Kobra S1",
    "Anycubic KX": "Anycubic Kobra X",
}
PHOTO_FIELDS = (
    "冷却参数照片",
    "温度塔照片",
    "最大体积流量照片",
    "流量比例照片",
    "PA校准照片",
    "小船45°模型",
    "综合模型45°",
    "面包机照片",
    "回抽测试",
    "其他照片",
)
ATTACHMENT_MAPPINGS = tuple(
    (source_field, "uploaded_json") for source_field in SOURCE_PROFILE_FIELDS
) + tuple((field, field) for field in PHOTO_FIELDS)

TARGET_PI_FIELD = "pi_code"
TARGET_PRINTER_FIELD = "printer"
TARGET_SUBMISSION_ID_FIELD = "submission_id"
TARGET_STATUS_FIELD = "status"
DRAFT = "DRAFT"
PAGE_SIZE = 100


class MigrationError(RuntimeError):
    """A migration operation failed or its configuration is invalid."""


def _first_present(fields: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if name in fields and fields[name] not in (None, "", []):
            return fields[name]
    return None


def _attachment_value(value: Any) -> list[dict[str, Any]]:
    """Return an ordered, detached copy suitable for an Attachment field."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []
    return copy.deepcopy([item for item in value if isinstance(item, dict)])


def upload_attachment_fields(
    api: BitableApi,
    source_fields: dict[str, Any],
    target_app: str,
) -> dict[str, list[dict[str, str]]]:
    """Download source attachments and return values with new tokens."""
    result: dict[str, list[dict[str, str]]] = {}
    for source_field, target_field in ATTACHMENT_MAPPINGS:
        attachments = _attachment_value(source_fields.get(source_field))
        if not attachments:
            if source_field in source_fields:
                result[target_field] = []
            continue
        uploaded: list[dict[str, str]] = []
        for index, attachment in enumerate(attachments, start=1):
            filename = str(attachment.get("name") or f"{source_field}-{index}.bin")
            print(f"    附件 {source_field} -> {target_field}/{filename}: 下载")
            content = api.download_attachment(attachment)
            print(f"    附件 {source_field} -> {target_field}/{filename}: 上传 ({len(content) / 1024:.0f}KB)")
            token = api.upload_attachment(target_app, filename, content)
            uploaded.append({"file_token": token})
        result[target_field] = uploaded
    return result


def migration_id(record_id: str, fields: dict[str, Any]) -> str:
    """Use an existing source ID when available, otherwise a stable ID."""
    value = fields.get(TARGET_SUBMISSION_ID_FIELD)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return f"MIGRATED-{record_id}"


def build_target_fields(record_id: str, source_fields: dict[str, Any]) -> dict[str, Any]:
    """Build only the approved migration field set."""
    result: dict[str, Any] = {
        TARGET_SUBMISSION_ID_FIELD: migration_id(record_id, source_fields),
        TARGET_STATUS_FIELD: DRAFT,
    }
    pi_code = _first_present(source_fields, SOURCE_PI_FIELDS)
    printer = _first_present(source_fields, SOURCE_PRINTER_FIELDS)
    if pi_code is not None:
        result[TARGET_PI_FIELD] = copy.deepcopy(pi_code)
    if printer is not None:
        result[TARGET_PRINTER_FIELD] = copy.deepcopy(printer)
    for field in PHOTO_FIELDS:
        if field in source_fields:
            result[field] = _attachment_value(source_fields[field])
    profile_field = next(
        (field for field in SOURCE_PROFILE_FIELDS if field in source_fields),
        None,
    )
    if profile_field:
        result["uploaded_json"] = _attachment_value(source_fields[profile_field])
    return result


class BitableApi:
    def __init__(self, env: dict[str, str]):
        missing = [
            key
            for key in ("FEISHU_APP_ID", "FEISHU_APP_SECRET")
            if not env.get(key)
        ]
        if missing:
            raise MigrationError(f".env 缺少配置: {', '.join(missing)}")
        auth = _api_json(
            AUTH_URL,
            token="",
            method="POST",
            payload={
                "app_id": env["FEISHU_APP_ID"],
                "app_secret": env["FEISHU_APP_SECRET"],
            },
        )
        self.token = auth["tenant_access_token"]
        self.parent_nodes: dict[str, str] = {}
        self.link_table_ids: dict[tuple[str, str], str] = {}
        self.link_records: dict[tuple[str, str], list[dict[str, Any]]] = {}

    def target_parent_node(self, app_token: str) -> str:
        if app_token not in self.parent_nodes:
            data = _api_json(f"{BITABLE_API}/apps/{app_token}", self.token).get("data", {})
            node = data.get("app", {}).get("app_token")
            if not node:
                raise MigrationError("目标 Base 元信息没有返回真实 app_token")
            self.parent_nodes[app_token] = str(node)
        return self.parent_nodes[app_token]

    def download_attachment(self, attachment: dict[str, Any]) -> bytes:
        url = _attachment_url(attachment)
        if not url:
            raise MigrationError("源附件缺少下载地址或 file_token")
        request = Request(url, headers={"Authorization": f"Bearer {self.token}"})
        try:
            with urlopen(request, timeout=120) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            raise MigrationError(f"下载附件失败: {exc}") from exc

    def upload_attachment(self, app_token: str, filename: str, content: bytes) -> str:
        boundary = f"----preset-worker-migration-{uuid.uuid4().hex}"
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        form_fields = {
            "file_name": filename or "migrated-attachment.bin",
            "parent_type": "bitable_file",
            "parent_node": self.target_parent_node(app_token),
            "size": str(len(content)),
        }
        body = bytearray()
        for key, value in form_fields.items():
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
            )
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode())
        body.extend(content)
        body.extend(f"\r\n--{boundary}--\r\n".encode())
        request = Request(
            UPLOAD_URL,
            data=bytes(body),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise MigrationError(f"上传附件失败: {exc}") from exc
        if result.get("code", 0) != 0:
            raise MigrationError(f"上传附件失败: {result.get('code')} {result.get('msg')}")
        token = result.get("data", {}).get("file_token")
        if not token:
            raise MigrationError("上传附件后没有返回 file_token")
        return str(token)

    def list_records(self, app_token: str, table_id: str) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        page_token = ""
        while True:
            query = {"page_size": str(PAGE_SIZE)}
            if page_token:
                query["page_token"] = page_token
            url = (
                f"{BITABLE_API}/apps/{app_token}/tables/{table_id}/records?"
                f"{urlencode(query)}"
            )
            data = _api_json(url, self.token).get("data", {})
            records.extend(data.get("items", []))
            if not data.get("has_more"):
                return records
            page_token = data.get("page_token", "")
            if not page_token:
                raise MigrationError("分页响应缺少 page_token")

    def linked_table_id(self, app_token: str, table_id: str, field_name: str) -> str:
        key = (table_id, field_name)
        if key not in self.link_table_ids:
            url = f"{BITABLE_API}/apps/{app_token}/tables/{table_id}/fields?page_size=100"
            items = _api_json(url, self.token).get("data", {}).get("items", [])
            field = next((item for item in items if item.get("field_name") == field_name), None)
            property_data = (field or {}).get("property") or {}
            linked_table = property_data.get("table_id")
            if not linked_table:
                raise MigrationError(f"目标字段 {field_name} 不是可解析的关联字段")
            self.link_table_ids[key] = str(linked_table)
        return self.link_table_ids[key]

    @staticmethod
    def _text_values(value: Any) -> list[str]:
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return [str(value)]
        if isinstance(value, list):
            values: list[str] = []
            for item in value:
                values.extend(BitableApi._text_values(item))
            return values
        if isinstance(value, dict):
            values: list[str] = []
            for key in ("text", "name", "value"):
                if value.get(key) not in (None, ""):
                    values.extend(BitableApi._text_values(value[key]))
            return values
        return []

    def resolve_link_value(
        self,
        app_token: str,
        target_table: str,
        field_name: str,
        source_value: Any,
    ) -> list[str]:
        """Resolve legacy text/link values to target SingleLink record IDs."""
        if isinstance(source_value, list):
            existing_ids = [
                str(item)
                for item in source_value
                if isinstance(item, str)
            ]
            existing_ids.extend(
                str(record_id)
                for item in source_value
                if isinstance(item, dict)
                for record_id in item.get("record_ids", [])
                if record_id
            )
            if existing_ids:
                return existing_ids
        wanted = self._text_values(source_value)
        if not wanted:
            return []
        if field_name == TARGET_PRINTER_FIELD:
            wanted = [PRINTER_VALUE_MAP.get(value, value) for value in wanted]
        wanted_set = {value.casefold() for value in wanted}
        linked_table = self.linked_table_id(app_token, target_table, field_name)
        cache_key = (app_token, linked_table)
        if cache_key not in self.link_records:
            self.link_records[cache_key] = self.list_records(app_token, linked_table)
        for record in self.link_records[cache_key]:
            values = {
                text.casefold()
                for value in (record.get("fields", {}) or {}).values()
                for text in self._text_values(value)
            }
            if wanted_set & values:
                record_id = record.get("record_id") or record.get("id")
                if record_id:
                    return [str(record_id)]
        raise MigrationError(
            f"目标关联字段 {field_name} 找不到源值: {', '.join(wanted)}"
        )

    def create_record(
        self, app_token: str, table_id: str, fields: dict[str, Any]
    ) -> dict[str, Any]:
        url = f"{BITABLE_API}/apps/{app_token}/tables/{table_id}/records"
        return _api_json(
            url,
            self.token,
            method="POST",
            payload={"fields": fields},
        ).get("data", {}).get("record", {})


def _existing_submission_ids(
    records: list[dict[str, Any]],
) -> set[str]:
    result: set[str] = set()
    for record in records:
        value = record.get("fields", {}).get(TARGET_SUBMISSION_ID_FIELD)
        if isinstance(value, str) and value:
            result.add(value)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--record-id", nargs="+", help="只迁移指定源 record_id")
    parser.add_argument("--limit", type=int, help="最多迁移多少条")
    parser.add_argument("--dry-run", action="store_true", help="只显示计划，不写入")
    parser.add_argument("--env", type=Path, default=Path(".env"), help="环境文件路径")
    args = parser.parse_args(argv)

    try:
        env = load_env(args.env)
        source_app = env.get(SOURCE_APP_ENV)
        source_table = env.get(SOURCE_TABLE_ENV)
        target_app = env.get(TARGET_APP_ENV)
        target_table = env.get(TARGET_TABLE_ENV)
        missing = [
            name
            for name, value in (
                (SOURCE_APP_ENV, source_app),
                (SOURCE_TABLE_ENV, source_table),
                (TARGET_APP_ENV, target_app),
                (TARGET_TABLE_ENV, target_table),
            )
            if not value
        ]
        if missing:
            raise MigrationError(f".env 缺少配置: {', '.join(missing)}")

        api = BitableApi(env)
        source_records = api.list_records(source_app, source_table)
        target_records = api.list_records(target_app, target_table)
        existing = _existing_submission_ids(target_records)

        if args.record_id:
            wanted = set(args.record_id)
            source_records = [
                record
                for record in source_records
                if record.get("record_id") in wanted
            ]
            found = {record.get("record_id") for record in source_records}
            missing_ids = wanted - found
            if missing_ids:
                raise MigrationError(
                    f"源表找不到 record_id: {', '.join(sorted(missing_ids))}"
                )

        plans: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
        for record in source_records:
            record_id = str(record.get("record_id") or "")
            source_fields = record.get("fields", {})
            fields = build_target_fields(record_id, source_fields)
            if TARGET_PI_FIELD in fields:
                fields[TARGET_PI_FIELD] = api.resolve_link_value(
                    target_app,
                    target_table,
                    TARGET_PI_FIELD,
                    fields[TARGET_PI_FIELD],
                )
            if TARGET_PRINTER_FIELD in fields:
                fields[TARGET_PRINTER_FIELD] = api.resolve_link_value(
                    target_app,
                    target_table,
                    TARGET_PRINTER_FIELD,
                    fields[TARGET_PRINTER_FIELD],
                )
            submission_id = fields[TARGET_SUBMISSION_ID_FIELD]
            if submission_id in existing:
                print(f"跳过 {record_id}: 目标已存在 {submission_id}")
                continue
            plans.append((record_id, source_fields, fields))
            if args.limit and len(plans) >= args.limit:
                break

        print(f"计划迁移 {len(plans)} 条，照片字段 {len(PHOTO_FIELDS)} 个")
        for record_id, _source_fields, fields in plans:
            photo_count = sum(len(fields.get(name, [])) for name in PHOTO_FIELDS)
            uploaded_json_count = len(fields.get("uploaded_json", []))
            print(
                f"  {record_id} -> {fields[TARGET_SUBMISSION_ID_FIELD]} "
                f"photos={photo_count} uploaded_json={uploaded_json_count}"
            )
        if args.dry_run:
            print("(--dry-run，未写入)")
            return 0

        completed = 0
        for record_id, source_fields, fields in plans:
            try:
                migrated_fields = copy.deepcopy(fields)
                migrated_fields.update(
                    upload_attachment_fields(api, source_fields, target_app)
                )
                created = api.create_record(target_app, target_table, migrated_fields)
                print(f"完成 {record_id} -> {created.get('record_id', '(unknown)')}")
                completed += 1
            except Exception as exc:
                print(f"失败 {record_id}: {exc}", file=sys.stderr)
        print(f"完成 {completed}/{len(plans)} 条")
        return 0 if completed == len(plans) else 1
    except (MigrationError, RuntimeError, ValueError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
