# P9-B1 Parser Design

## Boundary

The module is read-only and independent of Feishu, network access, Worker lifecycle, Miaoda, and preset comparison. It extracts Bambu Studio 3MF evidence and performs only verified configuration resolution.

## Modules

- three_mf/safe_zip.py: bounded ZIP metadata and streaming entry reads.
- three_mf/models.py: serializable dataclasses and explicit resolution statuses.
- three_mf/bambu_parser.py: project/model/slice/sequence/plate extraction and limited resolution.
- three_mf/diagnostics.py: standalone JSON diagnostic CLI.

Public functions:

    parse_bambu_3mf(artifact_or_bytes) -> BambuProjectSnapshot
    resolve_bambu_project(snapshot, ResolutionContext) -> ResolvedProjectSettings

Extraction and effective-value resolution are separate. A raw value can be extracted successfully while remaining UNRESOLVED.

## Supported entries

Required/known:

- Metadata/project_settings.config
- Metadata/model_settings.config
- Metadata/slice_info.config
- Metadata/filament_sequence.json
- Metadata/plate_N.json when present

Detected but not speculatively resolved:

- Metadata/filament_settings_*
- Metadata/machine_settings_*
- Metadata/process_settings_*

## Error handling

Malformed project JSON, model XML, slice metadata, sequence JSON, and plate JSON produce structured snapshot issues. Invalid ZIPs and resource-limit violations raise SafeZipError. No local path is included in parser error messages.

## CLI

    .venv/bin/python -m preset_worker.three_mf.diagnostics inspect project.3mf --output report.json

Optional context:

    --filament-slot N
    --plate N

The command never rewrites the input archive.

Priority extraction includes the four cooling fields fan_min_speed, fan_max_speed, fan_cooling_layer_time, and slow_down_layer_time. All four retain raw arrays and source paths.
