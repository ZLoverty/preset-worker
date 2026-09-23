"""Phase 1 workflow: enrich one Submission record.

This module deliberately stops before review and publication.  It only reads
Submission/Preset/PresetVersion records and writes enrichment fields back to
the same Submission.
"""

from __future__ import annotations

import json
import mimetypes
import copy
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


AUTH_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
BITABLE_API = "https://open.feishu.cn/open-apis/bitable/v1"
MEDIA_URL = "https://open.feishu.cn/open-apis/drive/v1/medias/{}/download"
UPLOAD_URL = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all"

SUBMISSION_TABLE_ENV = "FEISHU_SUBMISSION_TABLE_ID"
PRESET_TABLE_ENV = "FEISHU_TABLE_ID"
VERSION_TABLE_ENV = "FEISHU_VERSION_TABLE_ID"


def load_env(path: Path = Path(".env")) -> dict[str, str]:
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


def _api_json(url: str, token: str, *, method: str = "GET", payload: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"飞书 API 请求失败: {method} {url} -> HTTP {exc.code}: {detail or exc.reason}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"飞书 API 请求失败: {method} {url}: {exc}") from exc
    if result.get("code", 0) != 0:
        raise RuntimeError(
            f"飞书 API 错误 {result.get('code')}: {result.get('msg')} "
            f"({method} {url})"
        )
    return result


def _attachment_url(attachment: dict[str, Any]) -> str | None:
    url = attachment.get("url") or attachment.get("tmp_url")
    if url:
        return url
    token = attachment.get("file_token") or attachment.get("token")
    return MEDIA_URL.format(token) if token else None


def _attachment_list(value: object) -> list[dict[str, Any]]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if isinstance(value, dict):
        value = [value]
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


class FeishuClient:
    """Small Bitable adapter used by the enrichment service."""

    def __init__(self, env: dict[str, str]):
        missing = [key for key in ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_APP_TOKEN") if not env.get(key)]
        missing += [key for key in (SUBMISSION_TABLE_ENV, PRESET_TABLE_ENV, VERSION_TABLE_ENV) if not env.get(key)]
        if missing:
            raise RuntimeError(f".env 缺少配置: {', '.join(missing)}")
        auth = _api_json(
            AUTH_URL,
            token="",
            method="POST",
            payload={"app_id": env["FEISHU_APP_ID"], "app_secret": env["FEISHU_APP_SECRET"]},
        )
        self.token = auth["tenant_access_token"]
        self.app_token = env["FEISHU_APP_TOKEN"]
        app_info = _api_json(f"{BITABLE_API}/apps/{self.app_token}", self.token)
        self.parent_node = app_info.get("data", {}).get("app", {}).get("app_token", self.app_token)
        self.submission_table_id = env[SUBMISSION_TABLE_ENV]
        self.preset_table_id = env[PRESET_TABLE_ENV]
        self.version_table_id = env[VERSION_TABLE_ENV]

    def list_records(self, table_id: str) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        page_token = ""
        while True:
            query = {"page_size": "100"}
            if page_token:
                query["page_token"] = page_token
            url = f"{BITABLE_API}/apps/{self.app_token}/tables/{table_id}/records?{urlencode(query)}"
            data = _api_json(url, self.token).get("data", {})
            records.extend(data.get("items", []))
            if not data.get("has_more"):
                return records
            page_token = data.get("page_token", "")
            if not page_token:
                raise RuntimeError("分页响应缺少 page_token")

    def get_submission(self, submission_id: str) -> dict[str, Any]:
        for record in self.list_records(self.submission_table_id):
            fields = record.get("fields", {})
            if fields.get("submission_id") == submission_id:
                return record
        raise LookupError(f"找不到 submission: {submission_id}")

    def update_submission(self, record_id: str, fields: dict[str, Any]) -> None:
        url = f"{BITABLE_API}/apps/{self.app_token}/tables/{self.submission_table_id}/records/{record_id}"
        _api_json(url, self.token, method="PUT", payload={"fields": fields})

    def create_record(self, table_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        url = f"{BITABLE_API}/apps/{self.app_token}/tables/{table_id}/records"
        return _api_json(url, self.token, method="POST", payload={"fields": fields}).get("data", {}).get("record", {})

    def update_record(self, table_id: str, record_id: str, fields: dict[str, Any]) -> None:
        url = f"{BITABLE_API}/apps/{self.app_token}/tables/{table_id}/records/{record_id}"
        _api_json(url, self.token, method="PUT", payload={"fields": fields})

    def download_attachment(self, attachment: dict[str, Any]) -> bytes:
        url = _attachment_url(attachment)
        if not url:
            raise RuntimeError("附件缺少下载地址或 file_token")
        request = Request(url, headers={"Authorization": f"Bearer {self.token}"})
        try:
            with urlopen(request, timeout=120) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"下载附件失败: {exc}") from exc

    def upload_attachment(self, filename: str, content: bytes) -> dict[str, Any]:
        """Upload a file for use in a Bitable attachment field."""
        boundary = f"----preset-worker-{uuid.uuid4().hex}"
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        fields = {
            "file_name": filename,
            "parent_type": "bitable_file",
            # The upload API expects the canonical Bitable app token here.
            # The value in .env can be an alias, so use the token returned by
            # GET /bitable/v1/apps/{app_token}.
            "parent_node": self.parent_node,
            "size": str(len(content)),
        }
        body = bytearray()
        for key, value in fields.items():
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
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
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"上传 canonical_json 失败: HTTP {exc.code}: {detail or exc.reason}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"上传 canonical_json 失败: {exc}") from exc
        if result.get("code", 0) != 0:
            raise RuntimeError(f"上传 canonical_json 失败: {result.get('msg')}")
        return result.get("data", {})


def _lookup_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list) and value:
        return _lookup_text(value[0])
    if isinstance(value, dict):
        return str(value.get("text") or value.get("name") or "").strip()
    return ""


def _submission_method_version(fields: dict[str, Any]) -> str:
    # The deployed table calls this field method_version.  Keep the logical
    # P2 name pm_method_version at the processor boundary.
    value = fields.get("pm_method_version") or fields.get("method_version")
    return _lookup_text(value)


def validate_json(value: Any) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(value, dict):
        errors.append("JSON 顶层必须是 object")
    elif not all(isinstance(key, str) and key for key in value):
        errors.append("JSON object 的字段名必须是非空字符串")
    return {"valid": not errors, "errors": errors, "warnings": []}


class UnsupportedSlicerError(ValueError):
    pass


class BambuStudioProcessor:
    def __init__(self, *, pi_code: str, printer: str, pm_method_version: str):
        self.pi_code = pi_code
        self.printer = printer
        self.pm_method_version = pm_method_version

    def validate(self, uploaded: Any) -> dict[str, Any]:
        validation = validate_json(uploaded)
        if validation["valid"] and "version" not in uploaded:
            validation["valid"] = False
            validation["errors"].append("BambuStudio JSON 缺少必需字段: version")
        return validation

    def canonicalize(self, uploaded: Any) -> Any:
        # P2 has exactly two semantic canonicalization rules.  Deep-copying
        # protects uploaded_json from in-place mutation.
        canonical = copy.deepcopy(uploaded)
        canonical["name"] = f"{self.pi_code} @{self.printer}"
        canonical["pm_method_version"] = self.pm_method_version
        return canonical


def processor_for(slicer: str, *, pi_code: str, printer: str, pm_method_version: str) -> BambuStudioProcessor:
    if slicer != "BambuStudio":
        raise UnsupportedSlicerError(f"暂不支持 slicer: {slicer}")
    return BambuStudioProcessor(
        pi_code=pi_code,
        printer=printer,
        pm_method_version=pm_method_version,
    )


def _flatten(value: Any, path: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            result.update(_flatten(child, f"{path}.{key}" if path else key))
        return result
    if isinstance(value, list):
        result = {}
        for index, child in enumerate(value):
            result.update(_flatten(child, f"{path}[{index}]"))
        return result
    return {path: value}


def calculate_diff(old: Any | None, new: Any) -> dict[str, list[dict[str, Any]]]:
    new_flat = _flatten(new)
    if old is None:
        return {"added": [{"path": path, "new": value} for path, value in new_flat.items()], "removed": [], "modified": []}
    old_flat = _flatten(old)
    added = [{"path": path, "new": new_flat[path]} for path in new_flat.keys() - old_flat.keys()]
    removed = [{"path": path, "old": old_flat[path]} for path in old_flat.keys() - new_flat.keys()]
    modified = [
        {"path": path, "old": old_flat[path], "new": new_flat[path]}
        for path in new_flat.keys() & old_flat.keys()
        if old_flat[path] != new_flat[path]
    ]
    return {key: sorted(value, key=lambda item: item["path"]) for key, value in {"added": added, "removed": removed, "modified": modified}.items()}


def _json_field(value: object, default: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return value if value is not None else default


@dataclass
class EnrichmentResult:
    operation: str
    preset_key: str
    base_version_id: str
    canonical_json: Any
    diff: dict[str, Any]
    validation: dict[str, Any]
    status: str


class SubmissionEnrichment:
    def __init__(self, client: FeishuClient):
        self.client = client

    def _find_preset(self, preset_key: str) -> dict[str, Any] | None:
        return next(
            (record for record in self.client.list_records(self.client.preset_table_id)
             if _lookup_text(record.get("fields", {}).get("preset_key")) == preset_key),
            None,
        )

    def _base_json(self, preset: dict[str, Any]) -> tuple[str, str | None, Any | None]:
        preset_fields = preset.get("fields", {})
        base_version_id = _lookup_text(preset_fields.get("current_version_id"))
        if not base_version_id:
            base_version_id = _lookup_text(preset_fields.get("current_version"))
        if not base_version_id:
            return "", None, None
        versions = self.client.list_records(self.client.version_table_id)
        version = next(
            (item for item in versions if _lookup_text(item.get("fields", {}).get("version_id")) == base_version_id),
            None,
        )
        if not version:
            raise RuntimeError(f"找不到 base version: {base_version_id}")
        attachments = _attachment_list(version.get("fields", {}).get("canonical_json"))
        if not attachments:
            raise RuntimeError(f"base version 没有 canonical_json: {base_version_id}")
        try:
            return base_version_id, version.get("record_id") or version.get("id"), json.loads(
                self.client.download_attachment(attachments[0]).decode("utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"base version canonical_json 无法解析: {base_version_id}") from exc

    def _frozen_result(self, record: dict[str, Any]) -> EnrichmentResult:
        fields = record.get("fields", {})
        return EnrichmentResult(
            operation=str(fields.get("operation", "")),
            preset_key=str(fields.get("preset_key", "")),
            base_version_id=str(fields.get("base_version_id", "")),
            canonical_json={},
            diff=_json_field(fields.get("diff"), {}),
            validation=_json_field(fields.get("validation"), {}),
            status=str(fields.get("status", "READY_FOR_REVIEW")),
        )

    def enrich_submission(self, submission_id: str) -> EnrichmentResult:
        record = self.client.get_submission(submission_id)
        fields = record.get("fields", {})
        if fields.get("status") == "READY_FOR_REVIEW":
            return self._frozen_result(record)
        try:
            pi_code = _lookup_text(fields.get("pi_code"))
            printer = _lookup_text(fields.get("printer") or fields.get("machine"))
            slicer = _lookup_text(fields.get("slicer"))
            # preset_key is a Bitable formula field and is authoritative.
            preset_key = _lookup_text(fields.get("preset_key"))
            pm_method_version = _submission_method_version(fields)
            if not pi_code or not printer or not slicer or not preset_key:
                raise ValueError("Submission 缺少 pi_code、machine/printer、slicer 或公式 preset_key")
            if not pm_method_version:
                raise ValueError("Submission 缺少 pm_method_version（当前表字段为 method_version）")
        except ValueError as exc:
            validation = {"valid": False, "errors": [str(exc)], "warnings": []}
            self.client.update_submission(record["record_id"], {"validation": json.dumps(validation, ensure_ascii=False), "status": "VALIDATION_FAILED"})
            raise ValidationFailure(validation) from exc
        attachments = _attachment_list(fields.get("uploaded_json"))
        if not attachments:
            validation = {"valid": False, "errors": ["Submission 缺少 uploaded_json 附件"], "warnings": []}
            self.client.update_submission(record["record_id"], {"validation": json.dumps(validation, ensure_ascii=False), "status": "VALIDATION_FAILED"})
            raise ValidationFailure(validation)
        try:
            uploaded = json.loads(self.client.download_attachment(attachments[0]).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            validation = {"valid": False, "errors": [f"uploaded_json 不是有效 JSON: {exc}"], "warnings": []}
            self.client.update_submission(record["record_id"], {"validation": json.dumps(validation, ensure_ascii=False), "status": "VALIDATION_FAILED"})
            raise ValidationFailure(validation) from exc
        try:
            processor = processor_for(
                slicer,
                pi_code=pi_code,
                printer=printer,
                pm_method_version=pm_method_version,
            )
        except UnsupportedSlicerError as exc:
            validation = {"valid": False, "errors": [str(exc)], "warnings": []}
            self.client.update_submission(record["record_id"], {"validation": json.dumps(validation, ensure_ascii=False), "status": "VALIDATION_FAILED"})
            raise
        validation = processor.validate(uploaded)
        if not validation["valid"]:
            self.client.update_submission(record["record_id"], {"validation": json.dumps(validation, ensure_ascii=False), "status": "VALIDATION_FAILED"})
            raise ValidationFailure(validation)
        canonical = processor.canonicalize(uploaded)
        preset = self._find_preset(preset_key)
        operation = "UPDATE" if preset else "CREATE"
        base_version_id, base_version_record_id, base_json = self._base_json(preset) if preset else ("", None, None)
        diff = calculate_diff(base_json, canonical)
        canonical_bytes = json.dumps(canonical, ensure_ascii=False, indent=2).encode("utf-8")
        file_token = None
        existing_canonical = _attachment_list(fields.get("canonical_json"))
        if existing_canonical:
            try:
                existing = json.loads(self.client.download_attachment(existing_canonical[0]).decode("utf-8"))
                if existing == canonical:
                    file_token = existing_canonical[0].get("file_token") or existing_canonical[0].get("token")
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass
        if not file_token:
            uploaded_file = self.client.upload_attachment(f"{submission_id}_canonical.json", canonical_bytes)
            file_token = uploaded_file.get("file_token") or uploaded_file.get("token")
        if not file_token:
            raise RuntimeError("上传 canonical_json 后没有返回 file_token")
        result = EnrichmentResult(operation, preset_key, base_version_id, canonical, diff, validation, "READY_FOR_REVIEW")
        self.client.update_submission(
            record["record_id"],
            {
                "operation": result.operation,
                "base_version_id": [base_version_record_id] if base_version_record_id else [],
                "canonical_json": [{"file_token": file_token}],
                "diff": json.dumps(result.diff, ensure_ascii=False),
                "validation": json.dumps(result.validation, ensure_ascii=False),
                "status": result.status,
            },
        )
        return result


class ValidationFailure(ValueError):
    def __init__(self, validation: dict[str, Any]):
        super().__init__("Submission validation failed")
        self.validation = validation


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Enrich one Feishu Submission")
    parser.add_argument("submission_id")
    parser.add_argument("--env", type=Path, default=Path(".env"))
    args = parser.parse_args()
    try:
        result = SubmissionEnrichment(FeishuClient(load_env(args.env))).enrich_submission(args.submission_id)
    except ValidationFailure as exc:
        print(json.dumps(exc.validation, ensure_ascii=False, indent=2))
        return 2
    except (LookupError, RuntimeError, ValueError) as exc:
        print(f"错误: {exc}", file=__import__("sys").stderr)
        return 1
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
