"""Synchronize the PI Code x Printer CoverageTarget matrix."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable


@dataclass(frozen=True)
class CoverageFieldConfig:
    pi_identity: str = "PI Code"
    pi_enabled: str = "enabled"
    pi_importance: str = "Importance"
    printer_identity: str = "all_printers"
    printer_enabled: str = "enabled"
    printer_importance: str = "Importance"
    coverage_key: str = "coverage_key"
    coverage_pi: str = "pi_code"
    coverage_printer: str = "printer"
    coverage_importance: str = "importance"
    coverage_active: str = "active"


@dataclass(frozen=True)
class CoverageTableConfig:
    pi_table_id: str
    printer_table_id: str
    coverage_table_id: str
    fields: CoverageFieldConfig = field(default_factory=CoverageFieldConfig)
    importance_managed: bool = True

    @classmethod
    def from_env(cls, env: dict[str, str]) -> "CoverageTableConfig":
        names = (
            "FEISHU_PI_CODE_TABLE_ID",
            "FEISHU_PRINTER_TABLE_ID",
            "FEISHU_COVERAGE_TARGET_TABLE_ID",
        )
        missing = [name for name in names if not env.get(name)]
        if missing:
            raise ValueError(f"Missing .env values: {', '.join(missing)}")
        fields = CoverageFieldConfig(
            pi_identity=env.get("FEISHU_PI_CODE_FIELD", "PI Code"),
            pi_enabled=env.get("FEISHU_PI_CODE_ENABLED_FIELD", "enabled"),
            pi_importance=env.get("FEISHU_PI_CODE_IMPORTANCE_FIELD", "Importance"),
            printer_identity=env.get("FEISHU_PRINTER_FIELD", "all_printers"),
            printer_enabled=env.get("FEISHU_PRINTER_ENABLED_FIELD", "enabled"),
            printer_importance=env.get("FEISHU_PRINTER_IMPORTANCE_FIELD", "Importance"),
            coverage_key=env.get("FEISHU_COVERAGE_KEY_FIELD", "coverage_key"),
            coverage_pi=env.get("FEISHU_COVERAGE_PI_FIELD", "pi_code"),
            coverage_printer=env.get("FEISHU_COVERAGE_PRINTER_FIELD", "printer"),
            coverage_importance=env.get("FEISHU_COVERAGE_IMPORTANCE_FIELD", "importance"),
            coverage_active=env.get("FEISHU_COVERAGE_ACTIVE_FIELD", "active"),
        )
        return cls(env[names[0]], env[names[1]], env[names[2]], fields)


@dataclass(frozen=True)
class SourceRecord:
    identity: str
    record_id: str
    importance: int
    enabled: bool


@dataclass(frozen=True)
class CoveragePlan:
    key: str
    pi: SourceRecord
    printer: SourceRecord
    importance: int
    active: bool


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value).strip()
    if isinstance(value, list):
        return _text(value[0]) if value else ""
    if isinstance(value, dict):
        return _text(value.get("text") or value.get("name") or value.get("value"))
    return ""


def _record_id(record: dict[str, Any]) -> str:
    return str(record.get("record_id") or record.get("id") or "").strip()


def _importance(value: Any, label: str, errors: list[str]) -> int | None:
    raw = _text(value)
    if isinstance(value, bool) or raw not in {"0", "1"}:
        errors.append(f"{label}: importance must be integer 0 or 1, got {value!r}")
        return None
    return int(raw)


def _enabled(value: Any, label: str, errors: list[str]) -> bool | None:
    raw = _text(value).casefold()
    if raw in {"active", "enabled", "true", "1", "yes"}:
        return True
    if raw in {"inactive", "disabled", "false", "0", "no", "potential", "eol complete", "eol in progress"}:
        return False
    errors.append(f"{label}: unsupported enabled value {value!r}")
    return None


def _source_records(
    records: Iterable[dict[str, Any]],
    *,
    identity_field: str,
    importance_field: str,
    enabled_field: str,
    label: str,
    errors: list[str],
) -> list[SourceRecord]:
    result: list[SourceRecord] = []
    seen: dict[str, str] = {}
    for index, record in enumerate(records):
        fields = record.get("fields") or {}
        identity = _text(fields.get(identity_field))
        record_id = _record_id(record)
        prefix = f"{label}[{index}]"
        if not identity:
            errors.append(f"{prefix}: missing identity field {identity_field!r}")
            continue
        if not record_id:
            errors.append(f"{prefix} {identity!r}: missing record_id")
            continue
        identity_key = identity.casefold()
        if identity_key in seen:
            errors.append(f"duplicate {label} identity {identity!r}: records {seen[identity_key]} and {record_id}")
            continue
        seen[identity_key] = record_id
        importance = _importance(fields.get(importance_field), f"{prefix} {identity!r}", errors)
        enabled = True if not enabled_field else _enabled(fields.get(enabled_field), f"{prefix} {identity!r}", errors)
        if importance is not None and enabled is not None:
            result.append(SourceRecord(identity, record_id, importance, enabled))
    return result


def _coverage_fields(plan: CoveragePlan, config: CoverageFieldConfig, *, include_importance: bool = True) -> dict[str, Any]:
    values = {
        # Bitable link fields accept the associated record IDs directly.
        config.coverage_pi: [plan.pi.record_id],
        config.coverage_printer: [plan.printer.record_id],
        config.coverage_active: plan.active,
    }
    return values


def _relation_ids(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value.strip()} if value.strip() else set()
    if isinstance(value, list):
        result: set[str] = set()
        for item in value:
            result.update(_relation_ids(item))
        return result
    if isinstance(value, dict):
        return _relation_ids(value.get("record_ids") or value.get("record_id") or value.get("id"))
    return set()


def _managed_equal(name: str, current: Any, desired: Any, fields: CoverageFieldConfig) -> bool:
    if name in {fields.coverage_pi, fields.coverage_printer}:
        return _relation_ids(current) == _relation_ids(desired)
    if name == fields.coverage_key:
        return _text(current) == _text(desired)
    if name == fields.coverage_importance:
        return _text(current) == str(desired)
    if name == fields.coverage_active:
        return _is_active(current) == bool(desired)
    return current == desired


def build_plan(
    pi_records: list[dict[str, Any]],
    printer_records: list[dict[str, Any]],
    coverage_records: list[dict[str, Any]],
    config: CoverageTableConfig,
    *,
    field_names: set[str] | None = None,
) -> tuple[list[CoveragePlan], dict[str, dict[str, Any]], list[str], int, int, int]:
    errors: list[str] = []
    fields = config.fields
    if field_names is not None:
        required = {fields.coverage_pi, fields.coverage_printer, fields.coverage_active}
        missing = sorted(required - field_names)
        if missing:
            errors.append(f"CoverageTarget missing required fields: {', '.join(missing)}")

    pis = _source_records(pi_records, identity_field=fields.pi_identity, importance_field=fields.pi_importance, enabled_field=fields.pi_enabled, label="PI Code", errors=errors)
    printers = _source_records(printer_records, identity_field=fields.printer_identity, importance_field=fields.printer_importance, enabled_field=fields.printer_enabled, label="Printer", errors=errors)
    plans = [
        CoveragePlan(
            key=f"{pi.identity}@{printer.identity}",
            pi=pi,
            printer=printer,
            importance=pi.importance + printer.importance,
            active=pi.enabled and printer.enabled,
        )
        for pi in pis
        for printer in printers
    ]

    pi_by_id = {item.record_id: item for item in pis}
    printer_by_id = {item.record_id: item for item in printers}
    existing: dict[str, dict[str, Any]] = {}
    missing_key_count = 0
    orphan_count = 0
    for index, record in enumerate(coverage_records):
        record_id = _record_id(record)
        record_fields = record.get("fields") or {}
        key = _text(record_fields.get(fields.coverage_key))
        if not key:
            # Empty scaffolding rows cannot match a coverage key. Preserve
            # them, but do not let them block generation of the real matrix.
            pi_ids = _relation_ids(record_fields.get(fields.coverage_pi))
            printer_ids = _relation_ids(record_fields.get(fields.coverage_printer))
            if not pi_ids and not printer_ids:
                orphan_count += 1
                continue
            if len(pi_ids) == 1 and len(printer_ids) == 1 and next(iter(pi_ids)) in pi_by_id and next(iter(printer_ids)) in printer_by_id:
                key = f"{pi_by_id[next(iter(pi_ids))].identity}@{printer_by_id[next(iter(printer_ids))].identity}"
            else:
                missing_key_count += 1
                continue
        key_norm = key.casefold()
        if key_norm in existing:
            errors.append(f"duplicate CoverageTarget key {key!r}: records {_record_id(existing[key_norm])} and {record_id}")
            continue
        existing[key_norm] = record
    if missing_key_count:
        errors.append(f"CoverageTarget records missing {fields.coverage_key!r}: {missing_key_count}")
    return plans, existing, errors, sum(item.enabled for item in pis), sum(item.enabled for item in printers), orphan_count


def _is_active(value: Any) -> bool:
    return _text(value).casefold() in {"true", "1", "yes", "active"}


def summarize(plans: list[CoveragePlan], existing: dict[str, dict[str, Any]], config: CoverageTableConfig, errors: list[str], enabled_pi_codes: int, enabled_printers: int, orphan_count: int = 0) -> dict[str, Any]:
    fields = config.fields
    to_create = to_update = to_deactivate = unchanged = 0
    importance_distribution = {"0": 0, "1": 0, "2": 0}
    plan_keys = set()
    for plan in plans:
        plan_keys.add(plan.key.casefold())
        importance_distribution[str(plan.importance)] += 1
        current_record = existing.get(plan.key.casefold())
        if current_record is None:
            to_create += 1
            continue
        desired = _coverage_fields(plan, fields, include_importance=config.importance_managed)
        current = current_record.get("fields") or {}
        if any(not _managed_equal(name, current.get(name), value, fields) for name, value in desired.items()):
            to_update += 1
        else:
            unchanged += 1
    to_deactivate = sum(_is_active((record.get("fields") or {}).get(fields.coverage_active)) for key, record in existing.items() if key not in plan_keys)
    return {
        "enabled_pi_codes": enabled_pi_codes,
        "enabled_printers": enabled_printers,
        "expected_active_combination_count": sum(plan.active for plan in plans),
        "records_to_create": to_create,
        "records_to_update": to_update,
        "records_to_deactivate": to_deactivate,
        "unchanged_records": unchanged,
        "orphan_coverage_records": orphan_count,
        "importance_distribution": importance_distribution,
        "validation_errors": errors,
    }


def _pending_writes(plans: list[CoveragePlan], existing: dict[str, dict[str, Any]], config: CoverageTableConfig) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    fields = config.fields
    create_records = [_coverage_fields(plan, fields, include_importance=config.importance_managed) for plan in plans if plan.key.casefold() not in existing]
    active_keys = {plan.key.casefold() for plan in plans}
    update_records: list[dict[str, Any]] = []
    for plan in plans:
        record = existing.get(plan.key.casefold())
        if record is None:
            continue
        desired = _coverage_fields(plan, fields, include_importance=config.importance_managed)
        current = record.get("fields") or {}
        changed = {name: value for name, value in desired.items() if not _managed_equal(name, current.get(name), value, fields)}
        if changed:
            update_records.append({"record_id": _record_id(record), "fields": changed})
    for key, record in existing.items():
        if key not in active_keys and _is_active((record.get("fields") or {}).get(fields.coverage_active)):
            update_records.append({"record_id": _record_id(record), "fields": {fields.coverage_active: False}})
    return create_records, update_records


def synchronize(client: Any, config: CoverageTableConfig, *, dry_run: bool) -> dict[str, Any]:
    try:
        pi_records = client.list_records(config.pi_table_id)
        printer_records = client.list_records(config.printer_table_id)
        coverage_records = client.list_records(config.coverage_table_id)
        field_items = client.list_fields(config.coverage_table_id)
        field_names = {str(item.get("field_name")) for item in field_items}
    except Exception as exc:
        return {
            "enabled_pi_codes": 0,
            "enabled_printers": 0,
            "expected_active_combination_count": 0,
            "records_to_create": 0,
            "records_to_update": 0,
            "records_to_deactivate": 0,
            "unchanged_records": 0,
            "importance_distribution": {"0": 0, "1": 0, "2": 0},
            "validation_errors": [f"source read failed; no writes or deactivation allowed: {exc}"],
        }
    field_by_name = {str(item.get("field_name")): item for item in field_items}
    expected_ui_types = {config.fields.coverage_active: "Checkbox"}
    schema_errors = []
    for field_name, expected_ui_type in expected_ui_types.items():
        actual = field_by_name.get(field_name)
        if actual and actual.get("ui_type") != expected_ui_type:
            schema_errors.append(
                f"CoverageTarget field {field_name!r} must be {expected_ui_type}, got {actual.get('ui_type')!r}"
            )
    plans, existing, errors, enabled_pi_codes, enabled_printers, orphan_count = build_plan(pi_records, printer_records, coverage_records, config, field_names=field_names)
    errors.extend(schema_errors)
    summary = summarize(plans, existing, config, errors, enabled_pi_codes, enabled_printers, orphan_count)
    if dry_run or errors:
        return summary

    create_records, update_records = _pending_writes(plans, existing, config)
    try:
        if create_records:
            client.batch_create_records(config.coverage_table_id, create_records)
        if update_records:
            client.batch_update_records(config.coverage_table_id, update_records)
    except Exception as exc:
        # A batch endpoint may have committed part of a request before the
        # client observed an error. Re-read CoverageTarget and retry only the
        # still-missing/changed records, preventing duplicate creation.
        try:
            refreshed = client.list_records(config.coverage_table_id)
            refreshed_fields = {str(item.get("field_name")) for item in client.list_fields(config.coverage_table_id)}
            refreshed_plans, refreshed_existing, refreshed_errors, _, _, _ = build_plan(
                pi_records, printer_records, refreshed, config, field_names=refreshed_fields
            )
            if refreshed_errors:
                raise RuntimeError("; ".join(refreshed_errors))
            retry_create, retry_update = _pending_writes(refreshed_plans, refreshed_existing, config)
            if retry_create:
                client.batch_create_records(config.coverage_table_id, retry_create)
            if retry_update:
                client.batch_update_records(config.coverage_table_id, retry_update)
            summary["recovered_after_partial_failure"] = True
            summary["applied"] = True
        except Exception as recovery_exc:
            summary["validation_errors"].append(f"write partially failed; recovery also failed: {exc}; {recovery_exc}")
        return summary
    summary["applied"] = True
    return summary
