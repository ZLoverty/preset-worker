"""Phase 1 workflow: enrich one Submission record.

This module deliberately stops before review and publication.  It only reads
Submission/Preset/PresetVersion records and writes enrichment fields back to
the same Submission.
"""

from __future__ import annotations

import json
import mimetypes
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..slicers import Artifact, ProcessingContext, SlicerProcessorRegistry, process_artifact
from ..slicers.registry import default_processor_registry
from ..diff import UnifiedDiff, deserialize_unified_diff, serialize_unified_diff
from ..slicers.contracts import UnsupportedSlicerError
from ..profiling import current_timing


def _timed_download(client: Any, attachment: dict[str, Any], stage: str) -> bytes:
    timing = current_timing()
    if timing:
        with timing.stage(stage, summary_key="attachment_download_ms"):
            return client.download_attachment(attachment)
    return client.download_attachment(attachment)


def _timed_diff(processor: Any, base: Artifact | None, candidate: Artifact, context: ProcessingContext, *, operation: str) -> UnifiedDiff:
    timing = current_timing()
    if timing:
        with timing.stage(operation, summary_key="diff_ms"):
            return processor.diff(base, candidate, context)
    return processor.diff(base, candidate, context)


AUTH_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
BITABLE_API = "https://open.feishu.cn/open-apis/bitable/v1"
MEDIA_URL = "https://open.feishu.cn/open-apis/drive/v1/medias/{}/download"
UPLOAD_URL = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all"

SUBMISSION_TABLE_ENV = "FEISHU_SUBMISSION_TABLE_ID"
PRESET_TABLE_ENV = "FEISHU_TABLE_ID"
VERSION_TABLE_ENV = "FEISHU_VERSION_TABLE_ID"
PRESET_DATA_FIELD = "preset data"
LEGACY_PRESET_DATA_FIELD = "uploaded_json"
FORMAL_ENRICHMENT_STATUS = "VALIDATING"
BASE_VERSION_NO_TEXT_FIELD = "base_version_no_text"


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


def _api_json(url: str, token: str, *, method: str = "GET", payload: dict | None = None, retry_count: int = 0) -> dict:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None,
        headers=headers,
        method=method,
    )
    started = time.perf_counter()
    status: int | str = "error"
    try:
        with urlopen(request, timeout=30) as response:
            status = response.status
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        status = exc.code
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"飞书 API 请求失败: {method} {url} -> HTTP {exc.code}: {detail or exc.reason}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"飞书 API 请求失败: {method} {url}: {exc}") from exc
    succeeded = result.get("code", 0) == 0
    timing = current_timing()
    if timing:
        path = url.split("?", 1)[0]
        endpoint = "bitable_record" if "/records" in path else "bitable_app" if "/apps/" in path else "tenant_auth" if "/auth/" in path else "feishu_api"
        operation = "update_record" if method == "PUT" else "list_records" if path.endswith("/records") else "authenticate" if "/auth/" in path else "api_request"
        timing.api(operation=operation, method=method, endpoint=endpoint, duration_ms=(time.perf_counter() - started) * 1000, status=status, retry_count=retry_count, succeeded=succeeded)
    if not succeeded:
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


def _preset_data_attachments(fields: dict[str, Any]) -> list[dict[str, Any]]:
    """Read the renamed field, with a transition fallback for old records."""
    value = fields.get(PRESET_DATA_FIELD)
    if value in (None, "", []):
        value = fields.get(LEGACY_PRESET_DATA_FIELD)
    return _attachment_list(value)


class FeishuClient:
    """Small Bitable adapter used by the enrichment service."""

    def __init__(self, env: dict[str, str]):
        missing = [key for key in ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_APP_TOKEN") if not env.get(key)]
        missing += [key for key in (SUBMISSION_TABLE_ENV, PRESET_TABLE_ENV, VERSION_TABLE_ENV) if not env.get(key)]
        if missing:
            raise RuntimeError(f".env 缺少配置: {', '.join(missing)}")
        self.app_id = env["FEISHU_APP_ID"]
        self.app_secret = env["FEISHU_APP_SECRET"]
        self.token = ""
        self._token_refresh_at = 0.0
        self._authenticate()
        self.app_token = env["FEISHU_APP_TOKEN"]
        app_info = self._request_json(f"{BITABLE_API}/apps/{self.app_token}")
        self.parent_node = app_info.get("data", {}).get("app", {}).get("app_token", self.app_token)
        self.submission_table_id = env[SUBMISSION_TABLE_ENV]
        self.preset_table_id = env[PRESET_TABLE_ENV]
        self.version_table_id = env[VERSION_TABLE_ENV]

    def _authenticate(self) -> None:
        """Get a fresh tenant token and schedule a refresh before expiry."""
        auth = _api_json(
            AUTH_URL,
            token="",
            method="POST",
            payload={"app_id": self.app_id, "app_secret": self.app_secret},
        )
        self.token = auth["tenant_access_token"]
        try:
            expire = max(60, int(auth.get("expire", 7200)))
        except (TypeError, ValueError):
            expire = 7200
        self._token_refresh_at = time.monotonic() + expire - 60

    def _request_json(
        self,
        url: str,
        *,
        method: str = "GET",
        payload: dict | None = None,
    ) -> dict:
        """Call Feishu with proactive refresh and one invalid-token retry."""
        if time.monotonic() >= self._token_refresh_at:
            self._authenticate()
        try:
            return _api_json(url, self.token, method=method, payload=payload)
        except RuntimeError as exc:
            detail = str(exc)
            if "99991663" not in detail and "Invalid access token" not in detail:
                raise
            timing = current_timing()
            if timing:
                timing.retry_count += 1
            self._authenticate()
            return _api_json(url, self.token, method=method, payload=payload)

    def list_records(
        self,
        table_id: str,
        *,
        limit: int | None = None,
        filter_expression: str | None = None,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        page_token = ""
        while True:
            page_size = min(limit, 100) if limit else 100
            query = {"page_size": str(page_size)}
            if filter_expression:
                query["filter"] = filter_expression
            if page_token:
                query["page_token"] = page_token
            url = f"{BITABLE_API}/apps/{self.app_token}/tables/{table_id}/records?{urlencode(query)}"
            data = self._request_json(url).get("data", {})
            records.extend(data.get("items", []))
            if limit and len(records) >= limit:
                return records[:limit]
            if not data.get("has_more"):
                return records
            page_token = data.get("page_token", "")
            if not page_token:
                raise RuntimeError("分页响应缺少 page_token")

    def find_submission_candidates(
        self,
        status: str,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Find actionable Submission records using a server-side filter."""
        if limit <= 0:
            return []
        expression = f'CurrentValue.[status]="{status}"'
        return self.list_records(
            self.submission_table_id,
            limit=limit,
            filter_expression=expression,
        )

    def list_preview_candidates(self, *, limit: int) -> list[dict[str, Any]]:
        """Find explicit preview requests without loading inactive records."""
        return self.find_submission_candidates("PREVIEW_REQUESTED", limit=limit)

    def get_submission(self, submission_id: str) -> dict[str, Any]:
        for record in self.list_records(self.submission_table_id):
            record_id = record.get("record_id") or record.get("id")
            fields = record.get("fields", {})
            field_submission_id = _lookup_text(fields.get("submission_id"))
            if submission_id in {record_id, field_submission_id}:
                return record
        raise LookupError(f"找不到 submission: {submission_id}")

    def update_submission(self, record_id: str, fields: dict[str, Any]) -> None:
        url = f"{BITABLE_API}/apps/{self.app_token}/tables/{self.submission_table_id}/records/{record_id}"
        self._request_json(url, method="PUT", payload={"fields": fields})

    def get_record(self, table_id: str, record_id: str) -> dict[str, Any]:
        """Fetch a record by native Bitable record_id only."""
        url = f"{BITABLE_API}/apps/{self.app_token}/tables/{table_id}/records/{record_id}"
        return self._request_json(url).get("data", {}).get("record", {})

    def find_preset_by_key(self, preset_key: str) -> list[dict[str, Any]]:
        """Use an exact server-side filter for the formula-backed key."""
        escaped = preset_key.replace(chr(34), chr(92) + chr(34))
        return self.list_records(
            self.preset_table_id,
            filter_expression=f'CurrentValue.[preset_key]="{escaped}"',
        )

    def create_record(self, table_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        url = f"{BITABLE_API}/apps/{self.app_token}/tables/{table_id}/records"
        return self._request_json(url, method="POST", payload={"fields": fields}).get("data", {}).get("record", {})

    def update_record(self, table_id: str, record_id: str, fields: dict[str, Any]) -> None:
        url = f"{BITABLE_API}/apps/{self.app_token}/tables/{table_id}/records/{record_id}"
        self._request_json(url, method="PUT", payload={"fields": fields})

    def download_attachment(self, attachment: dict[str, Any]) -> bytes:
        url = _attachment_url(attachment)
        if not url:
            raise RuntimeError("附件缺少下载地址或 file_token")
        request = Request(url, headers={"Authorization": f"Bearer {self.token}"})
        started = time.perf_counter()
        try:
            with urlopen(request, timeout=120) as response:
                content = response.read()
                timing = current_timing()
                if timing:
                    timing.api(operation="download_attachment", method="GET", endpoint="media_download", duration_ms=(time.perf_counter() - started) * 1000, status=response.status, retry_count=0, succeeded=True)
                return content
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
        started = time.perf_counter()
        try:
            with urlopen(request, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"上传 canonical_json 失败: HTTP {exc.code}: {detail or exc.reason}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"上传 canonical_json 失败: {exc}") from exc
        timing = current_timing()
        if timing:
            timing.api(operation="upload_attachment", method="POST", endpoint="media_upload", duration_ms=(time.perf_counter() - started) * 1000, status=response.status, retry_count=0, succeeded=result.get("code", 0) == 0)
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


def _link_record_ids(value: object) -> list[str]:
    """Extract record IDs from a Bitable SingleLink value."""
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_link_record_ids(item))
        return result
    if isinstance(value, dict):
        return [str(record_id) for record_id in value.get("record_ids", []) if record_id]
    return []


def _version_no(record: dict[str, Any]) -> str:
    value = record.get("fields", {}).get("version_no")
    if value in (None, "") or isinstance(value, bool):
        raise RuntimeError("PresetVersion 缺少 version_no")
    return str(value)


def _submission_method_version(fields: dict[str, Any]) -> str:
    # The deployed table calls this field method_version.  Keep the logical
    # P2 name pm_method_version at the processor boundary.
    value = fields.get("pm_method_version") or fields.get("method_version")
    return _lookup_text(value)


def _json_field(value: object, default: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return value if value is not None else default


@dataclass
class CandidateResult:
    operation: str
    preset_key: str
    base_version_id: str
    base_version_record_id: str | None
    base_version_no_text: str
    canonical_artifact: Artifact
    diff: UnifiedDiff
    validation: dict[str, Any]


@dataclass
class EnrichmentResult(CandidateResult):
    status: str


class CandidateFailure(ValueError):
    """A candidate is invalid feedback, rather than an infrastructure error."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class SubmissionEnrichment:
    def __init__(self, client: FeishuClient, *, processor_registry: SlicerProcessorRegistry | None = None):
        self.client = client
        self.processor_registry = processor_registry or default_processor_registry()

    def _find_preset(self, preset_key: str) -> dict[str, Any] | None:
        find_filtered = getattr(self.client, "find_preset_by_key", None)
        if callable(find_filtered):
            candidates = list(find_filtered(preset_key))
        else:
            candidates = self.client.list_records(self.client.preset_table_id)
        matches = [
            record for record in candidates
            if _lookup_text(record.get("fields", {}).get("preset_key")) == preset_key
        ]
        if len(matches) > 1:
            raise CandidateFailure(f"preset_key 存在重复 Preset: {preset_key}")
        return matches[0] if matches else None

    def _base_artifact(self, preset: dict[str, Any]) -> tuple[str, str | None, str, Artifact]:
        preset_fields = preset.get("fields", {})
        base_version_id = _lookup_text(preset_fields.get("current_version_id"))
        if not base_version_id:
            base_version_id = _lookup_text(preset_fields.get("current_version"))
        if not base_version_id:
            raise CandidateFailure("匹配的 Preset 缺少 current_version")
        versions = self.client.list_records(self.client.version_table_id)
        version = next(
            (item for item in versions if _lookup_text(item.get("fields", {}).get("version_id")) == base_version_id),
            None,
        )
        if not version:
            raise RuntimeError(f"找不到 base version: {base_version_id}")
        base_version_no_text = _version_no(version)
        attachments = _attachment_list(version.get("fields", {}).get("canonical_json"))
        if not attachments:
            raise RuntimeError(f"base version 没有 canonical_json: {base_version_id}")
        attachment = attachments[0]
        content = _timed_download(self.client, attachment, "base_attachment_download")
        filename = str(attachment.get("name") or attachment.get("file_name") or f"{base_version_id}.artifact")
        media_type = attachment.get("type") or attachment.get("mime_type")
        return base_version_id, version.get("record_id") or version.get("id"), base_version_no_text, Artifact(
            content=content,
            filename=filename,
            media_type=media_type,
        )

    def _frozen_result(self, record: dict[str, Any]) -> EnrichmentResult:
        fields = record.get("fields", {})
        return EnrichmentResult(
            operation=str(fields.get("operation", "")),
            preset_key=str(fields.get("preset_key", "")),
            base_version_id=str(fields.get("base_version_id", "")),
            base_version_record_id=None,
            base_version_no_text=str(fields.get(BASE_VERSION_NO_TEXT_FIELD, "")),
            canonical_artifact=Artifact(b"", "", None),
            diff=deserialize_unified_diff(fields.get("diff", "{}")),
            validation=_json_field(fields.get("validation"), {}),
            status=str(fields.get("status", "READY_FOR_REVIEW")),
        )

    def process_candidate(self, record: dict[str, Any], submission_id: str) -> CandidateResult:
        """Compute a candidate without changing Submission or publication tables."""
        fields = record.get("fields", {})
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
            raise ValidationFailure({"valid": False, "errors": [str(exc)], "warnings": []}) from exc

        attachments = _preset_data_attachments(fields)
        if not attachments:
            raise ValidationFailure({"valid": False, "errors": ["Submission 缺少 uploaded_json 附件"], "warnings": []})
        uploaded_attachment = attachments[0]
        artifact = Artifact(
            content=_timed_download(self.client, uploaded_attachment, "uploaded_attachment_download"),
            filename=str(uploaded_attachment.get("name") or uploaded_attachment.get("file_name") or f"{submission_id}.artifact"),
            media_type=uploaded_attachment.get("type") or uploaded_attachment.get("mime_type"),
        )
        processor = self.processor_registry.get(slicer)
        if processor is None:
            # Keep the historical exception/API while making the failure
            # machine-readable through UnsupportedSlicerError.validation.
            raise UnsupportedSlicerError(slicer)
        context = ProcessingContext(
            pi_code=pi_code,
            printer=printer,
            slicer=slicer,
            pm_method_version=pm_method_version,
        )
        timing = current_timing()
        try:
            if timing:
                with timing.stage("processor", summary_key="processor_ms"):
                    processed = process_artifact(processor, artifact, context)
            else:
                processed = process_artifact(processor, artifact, context)
        except ValueError as exc:
            validation = getattr(exc, "validation", None)
            if validation is not None:
                raise ValidationFailure(validation.as_dict()) from exc
            raise
        validation = processed.validation_result.as_dict()
        if not processed.validation_result.valid:
            raise ValidationFailure(validation)
        if timing:
            with timing.stage("preset_lookup", summary_key="feishu_read_ms"):
                preset = self._find_preset(preset_key)
        else:
            preset = self._find_preset(preset_key)
        operation = "UPDATE" if preset else "CREATE"
        base_version_id, base_version_record_id, base_version_no_text, base_artifact = (
            self._base_artifact(preset) if preset else ("", None, "", None)
        )
        return CandidateResult(
            operation=operation,
            preset_key=preset_key,
            base_version_id=base_version_id,
            base_version_record_id=base_version_record_id,
            base_version_no_text=base_version_no_text,
            canonical_artifact=processed.canonical_artifact,
            diff=(
                _timed_diff(processor, base_artifact, processed.canonical_artifact, context, operation="diff_update")
                if operation == "UPDATE"
                else _timed_diff(processor, None, processed.canonical_artifact, context, operation="diff_create")
            ),
            validation=validation,
        )

    def _canonical_attachment(self, record: dict[str, Any], submission_id: str, canonical_artifact: Artifact) -> str:
        fields = record.get("fields", {})
        existing_canonical = _attachment_list(fields.get("canonical_json"))
        if existing_canonical:
            existing = _timed_download(self.client, existing_canonical[0], "existing_canonical_download")
            if existing == canonical_artifact.content:
                file_token = existing_canonical[0].get("file_token") or existing_canonical[0].get("token")
                if file_token:
                    return file_token
        filename = canonical_artifact.filename or f"{submission_id}.artifact"
        timing = current_timing()
        if timing:
            with timing.stage("canonical_attachment_upload", summary_key="attachment_upload_ms"):
                uploaded_file = self.client.upload_attachment(filename, canonical_artifact.content)
        else:
            uploaded_file = self.client.upload_attachment(filename, canonical_artifact.content)
        file_token = uploaded_file.get("file_token") or uploaded_file.get("token")
        if not file_token:
            raise RuntimeError("上传 canonical_json 后没有返回 file_token")
        return file_token

    def enrich_submission(self, submission_id: str) -> EnrichmentResult:
        record = self.client.get_submission(submission_id)
        fields = record.get("fields", {})
        if fields.get("status") == "READY_FOR_REVIEW":
            return self._frozen_result(record)
        if fields.get("status") != FORMAL_ENRICHMENT_STATUS:
            raise RuntimeError(
                f"Submission is {fields.get('status', 'unknown')} and is not eligible for formal enrichment."
            )
        try:
            candidate = self.process_candidate(record, submission_id)
        except ValidationFailure as exc:
            self.client.update_submission(record["record_id"], {"validation": json.dumps(exc.validation, ensure_ascii=False), "status": "VALIDATION_FAILED"})
            raise
        except CandidateFailure as exc:
            validation = {"valid": False, "errors": [str(exc)], "warnings": []}
            self.client.update_submission(record["record_id"], {"validation": json.dumps(validation, ensure_ascii=False), "status": "VALIDATION_FAILED"})
            raise ValidationFailure(validation) from exc
        except UnsupportedSlicerError as exc:
            validation = {"valid": False, "errors": [str(exc)], "warnings": []}
            self.client.update_submission(record["record_id"], {"validation": json.dumps(validation, ensure_ascii=False), "status": "VALIDATION_FAILED"})
            raise
        file_token = self._canonical_attachment(record, submission_id, candidate.canonical_artifact)
        result = EnrichmentResult(**candidate.__dict__, status="READY_FOR_REVIEW")
        self.client.update_submission(
            record["record_id"],
            {
                "operation": result.operation,
                "base_version_id": [candidate.base_version_record_id]
                if candidate.base_version_record_id
                else [],
                BASE_VERSION_NO_TEXT_FIELD: candidate.base_version_no_text,
                "canonical_json": [{"file_token": file_token}],
                "diff": serialize_unified_diff(result.diff),
                "validation": json.dumps(result.validation, ensure_ascii=False),
                "status": result.status,
            },
        )
        return result

    def backfill_base_version_no_text(self, *, limit: int | None = None) -> dict[str, int]:
        """Repair historical UPDATE submissions from their linked base version.

        This deliberately never consults Preset.current_version and only sends
        the derived text field in each update request.
        """
        records = self.client.list_records(self.client.submission_table_id)
        scanned = repaired = skipped = 0
        versions = self.client.list_records(self.client.version_table_id)
        for record in records:
            if limit is not None and repaired >= limit:
                break
            scanned += 1
            fields = record.get("fields", {})
            base_value = fields.get("base_version_id") or fields.get("base_version")
            if not _link_record_ids(base_value) or _lookup_text(fields.get(BASE_VERSION_NO_TEXT_FIELD)):
                skipped += 1
                continue
            linked_ids = set(_link_record_ids(base_value))
            version = next(
                (
                    item for item in versions
                    if str(item.get("record_id") or item.get("id") or "") in linked_ids
                ),
                None,
            )
            if version is None:
                raise RuntimeError(f"Submission {record.get('record_id', '')} 的 base_version 关联记录不存在")
            value = _version_no(version)
            self.client.update_submission(record["record_id"], {BASE_VERSION_NO_TEXT_FIELD: value})
            repaired += 1
        return {"scanned": scanned, "repaired": repaired, "skipped": skipped}


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
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2, default=_json_default))
    return 0


def _json_default(value: object) -> object:
    if isinstance(value, Artifact):
        return {
            "filename": value.filename,
            "media_type": value.media_type,
            "size": len(value.content),
        }
    if isinstance(value, UnifiedDiff):
        return value.to_dict()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


if __name__ == "__main__":
    raise SystemExit(main())
