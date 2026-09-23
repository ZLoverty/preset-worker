"""P3: publish an approved Submission into Preset and PresetVersion."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from submission_enrichment import FeishuClient, _attachment_list, _lookup_text, load_env


APPROVING = "APPROVING"
APPROVED = "APPROVED"
VERSION_CONFLICT = "VERSION_CONFLICT"


class PublicationConflict(RuntimeError):
    """The approved operation can no longer be published safely."""


def _link_record_ids(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    ids: list[str] = []
    for item in value:
        if isinstance(item, str):
            ids.append(item)
        elif isinstance(item, dict):
            ids.extend(str(record_id) for record_id in item.get("record_ids", []) if record_id)
    return ids


def _person_snapshot(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    people: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict) and item.get("id"):
            people.append({"id": str(item["id"])})
    return people


def _version_no(record: dict[str, Any] | None) -> int | None:
    if not record:
        return None
    value = record.get("fields", {}).get("version_no")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _current_version_text(preset: dict[str, Any]) -> str:
    fields = preset.get("fields", {})
    return _lookup_text(fields.get("current_version") or fields.get("current_version_id"))


def _current_version_record_id(preset: dict[str, Any]) -> str | None:
    fields = preset.get("fields", {})
    ids = _link_record_ids(fields.get("current_version") or fields.get("current_version_id"))
    return ids[0] if ids else None


@dataclass
class PublicationResult:
    submission_id: str
    preset_key: str
    version_id: str
    version_no: int
    recovered: bool = False


class SubmissionPublisher:
    def __init__(self, client: FeishuClient):
        self.client = client

    def _find_submission_version(self, submission: dict[str, Any]) -> dict[str, Any] | None:
        submission_record_id = submission["record_id"]
        submission_id = submission.get("fields", {}).get("submission_id")
        for version in self.client.list_records(self.client.version_table_id):
            relation = version.get("fields", {}).get("source_submission")
            if submission_record_id in _link_record_ids(relation):
                return version
            if submission_id and _lookup_text(relation) == str(submission_id):
                return version
        return None

    def _find_preset(self, preset_key: str) -> dict[str, Any] | None:
        for preset in self.client.list_records(self.client.preset_table_id):
            if _lookup_text(preset.get("fields", {}).get("preset_key")) == preset_key:
                return preset
        return None

    def _find_version(self, version_id: str) -> dict[str, Any] | None:
        for version in self.client.list_records(self.client.version_table_id):
            if _lookup_text(version.get("fields", {}).get("version_id")) == version_id:
                return version
        return None

    def _set_submission_published(self, submission: dict[str, Any], version_id: str) -> None:
        self.client.update_submission(
            submission["record_id"],
            {"published_version_id": version_id, "status": APPROVED},
        )

    def _project_process_photos(self, preset: dict[str, Any], submission: dict[str, Any]) -> None:
        submission_fields = submission.get("fields", {})
        photos = submission_fields.get("process_photos")
        if photos is None:
            photos = submission_fields.get("photos")
        if photos is not None and "photos" in preset.get("fields", {}):
            self.client.update_record(
                self.client.preset_table_id,
                preset["record_id"],
                {"photos": photos},
            )

    def _repair_existing(
        self,
        submission: dict[str, Any],
        preset: dict[str, Any],
        version: dict[str, Any],
    ) -> PublicationResult:
        fields = submission.get("fields", {})
        version_fields = version.get("fields", {})
        version_no = _version_no(version)
        version_id = _lookup_text(version_fields.get("version_id"))
        if not version_id and version_no is not None:
            version_id = f"{_lookup_text(fields.get('preset_key'))}@v{version_no}"
        if not version_id or version_no is None:
            raise RuntimeError("已有 PresetVersion 缺少 version_id 或 version_no")

        current_no = _version_no(self._find_version(_current_version_text(preset)))
        current_record_id = _current_version_record_id(preset)
        if current_no is None or current_no <= version_no:
            if current_record_id != version["record_id"]:
                self.client.update_record(
                    self.client.preset_table_id,
                    preset["record_id"],
                    {"current_version": [version["record_id"]]},
                )
                preset = self._find_preset(_lookup_text(fields.get("preset_key"))) or preset
            self._project_process_photos(preset, submission)
        # If a newer version is current, never roll it back.  The source
        # Submission can still be marked as published against its own version.
        self._set_submission_published(submission, version_id)
        return PublicationResult(
            str(fields.get("submission_id", submission["record_id"])),
            _lookup_text(fields.get("preset_key")),
            version_id,
            version_no,
            recovered=True,
        )

    def _create_preset(self, submission: dict[str, Any], preset_key: str) -> dict[str, Any]:
        fields = submission.get("fields", {})
        preset_fields: dict[str, Any] = {"preset_key": preset_key}
        for target, source in (("pi_code", "pi_code"), ("printer", "printer"), ("slicer", "slicer")):
            ids = _link_record_ids(fields.get(source))
            if ids:
                preset_fields[target] = ids
        return self.client.create_record(self.client.preset_table_id, preset_fields)

    def _version_fields(self, submission: dict[str, Any], preset_key: str, version_no: int) -> dict[str, Any]:
        fields = submission.get("fields", {})
        attachments = _attachment_list(fields.get("canonical_json"))
        if not attachments:
            raise RuntimeError("Submission 缺少 canonical_json 附件")
        file_token = attachments[0].get("file_token") or attachments[0].get("token")
        if not file_token:
            raise RuntimeError("canonical_json 附件缺少 file_token")
        now = int(time.time() * 1000)
        result: dict[str, Any] = {
            "preset_key": preset_key,
            "version_no": version_no,
            "canonical_json": [{"file_token": file_token}],
            "source_submission": [submission["record_id"]],
            "created_at": now,
        }
        for field in ("change_reason", "review_comment"):
            if fields.get(field) is not None:
                result[field] = fields[field]
        for target, source in (("submitted_by", "submitter"), ("reviewed_by", "reviewer")):
            people = _person_snapshot(fields.get(source))
            if people:
                result[target] = people
        for field in ("submitted_at", "reviewed_at"):
            if fields.get(field) is not None:
                result[field] = fields[field]
        return result

    def publish_submission(self, submission_id: str) -> PublicationResult:
        submission = self.client.get_submission(submission_id)
        fields = submission.get("fields", {})
        status = fields.get("status")
        existing_version = self._find_submission_version(submission)
        if status == APPROVED and existing_version:
            return self._repair_existing(
                submission,
                self._find_preset(_lookup_text(fields.get("preset_key"))) or {},
                existing_version,
            )
        if status != APPROVING:
            raise RuntimeError(f"Submission {submission_id} 状态不是 APPROVING: {status}")

        preset_key = _lookup_text(fields.get("preset_key"))
        if not preset_key:
            raise RuntimeError("Submission 缺少 preset_key")

        preset = self._find_preset(preset_key)
        operation = fields.get("operation")
        if existing_version:
            if not preset:
                raise PublicationConflict("已有 PresetVersion，但找不到对应 Preset")
            return self._repair_existing(submission, preset, existing_version)

        if operation == "UPDATE":
            if not preset:
                raise PublicationConflict("UPDATE Submission 对应的 Preset 不存在")
            base_version = _lookup_text(fields.get("base_version_id"))
            current_version = _current_version_text(preset)
            if base_version != current_version:
                self.client.update_submission(submission["record_id"], {"status": VERSION_CONFLICT})
                raise PublicationConflict(f"版本冲突: base={base_version}, current={current_version}")
            current_version_record = self._find_version(current_version)
            current_no = _version_no(current_version_record)
            if current_no is None:
                raise RuntimeError(f"当前版本缺少 version_no: {current_version}")
            version_no = current_no + 1
        elif operation == "CREATE":
            if preset:
                self.client.update_submission(submission["record_id"], {"status": VERSION_CONFLICT})
                raise PublicationConflict("CREATE Submission 的 preset_key 已存在")
            preset = self._create_preset(submission, preset_key)
            version_no = 1
        else:
            raise RuntimeError(f"不支持的 operation: {operation}")

        version_id = f"{preset_key}@v{version_no}"
        version = self.client.create_record(
            self.client.version_table_id,
            self._version_fields(submission, preset_key, version_no),
        )
        version_record_id = version.get("record_id") or version.get("id")
        if not version_record_id:
            raise RuntimeError("创建 PresetVersion 后没有返回 record_id")
        self.client.update_record(
            self.client.preset_table_id,
            preset["record_id"],
            {"current_version": [version_record_id]},
        )
        self._project_process_photos(preset, submission)
        self._set_submission_published(submission, version_id)
        return PublicationResult(
            submission_id,
            preset_key,
            version_id,
            version_no,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish one APPROVING Submission")
    parser.add_argument("submission_id")
    parser.add_argument("--env", type=Path, default=Path(".env"))
    args = parser.parse_args()
    try:
        result = SubmissionPublisher(FeishuClient(load_env(args.env))).publish_submission(args.submission_id)
    except (LookupError, RuntimeError, ValueError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
