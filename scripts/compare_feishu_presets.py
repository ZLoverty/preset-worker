"""Compare Feishu-exported presets with local expanded BambuStudio presets.

The command is read-only against Feishu. It downloads the JSON attachment from
the preset table, matches it to a local file by PI code and printer, and emits
JSON, CSV, and a small HTML report.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


AUTH_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
BITABLE_API = "https://open.feishu.cn/open-apis/bitable/v1"
MEDIA_URL = "https://open.feishu.cn/open-apis/drive/v1/medias/{}/download"
DEFAULT_PRESET_TABLE = "tblVz1q8G93W6aLg"
DEFAULT_MAPPING_TABLE = "tblPQnLTactABfxQ"
DEFAULT_LOCAL_ROOTS = {
    "bambustudio": Path(r"C:\Users\zhengyang\Downloads\BambuStudio_filtered_presets"),
    "crealityprint": Path(r"C:\Users\zhengyang\Downloads\CrealityPrint_filtered_presets"),
    "elegooslicer": Path(r"C:\Users\zhengyang\Downloads\ElegooSlicer_filtered_presets"),
    "orcaslicer": Path(r"C:\Users\zhengyang\Downloads\OrcaSlicer_filtered_presets"),
    "snapmakerorcaslicer": Path(r"C:\Users\zhengyang\Downloads\SnapmakerOrcaSlicer_filtered_presets"),
    "prusaslicer": Path(r"C:\Users\zhengyang\Downloads\PrusaSlicer_filtered_presets"),
}
DEFAULT_SLICERS = (
    "BambuStudio",
    "CrealityPrint",
    "ElegooSlicer",
    "OrcaSlicer",
    "SnapmakerOrcaSlicer",
    "PrusaSlicer",
)
FEISHU_SLICER_NAMES = {
    "SnapmakerOrcaSlicer": ("OrcaSlicer (Snapmaker)",),
}

METADATA_KEYS = {
    "from", "name", "type", "include", "version", "inherits", "setting_id",
    "description", "instantiation", "filament_id", "compatible_printers",
    "filament_settings_id", "filament_vendor", "compatible_printers_condition",
    "compatible_prints", "compatible_prints_condition",
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


def api_json(url: str, token: str | None = None, payload: dict | None = None) -> dict:
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
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Feishu request failed: {exc}") from exc
    if result.get("code", 0) != 0:
        raise RuntimeError(f"Feishu API error {result.get('code')}: {result.get('msg')}")
    return result


class FeishuClient:
    def __init__(self, env: dict[str, str]) -> None:
        required = ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_APP_TOKEN")
        missing = [key for key in required if not env.get(key)]
        if missing:
            raise RuntimeError(f"Missing .env values: {', '.join(missing)}")
        auth = api_json(
            AUTH_URL,
            payload={"app_id": env["FEISHU_APP_ID"], "app_secret": env["FEISHU_APP_SECRET"]},
        )
        self.token = auth["tenant_access_token"]
        self.app = env["FEISHU_APP_TOKEN"]

    def records(self, table_id: str) -> list[dict]:
        records: list[dict] = []
        page_token = ""
        while True:
            query = {"page_size": "100"}
            if page_token:
                query["page_token"] = page_token
            url = f"{BITABLE_API}/apps/{self.app}/tables/{table_id}/records?{urlencode(query)}"
            data = api_json(url, self.token).get("data", {})
            records.extend(data.get("items", []))
            if not data.get("has_more"):
                return records
            page_token = data.get("page_token", "")
            if not page_token:
                raise RuntimeError("Feishu pagination response has no page_token")

    def download_attachment(self, token: str, destination: Path) -> None:
        request = Request(MEDIA_URL.format(token), headers={"Authorization": f"Bearer {self.token}"})
        try:
            with urlopen(request, timeout=120) as response:
                destination.write_bytes(response.read())
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            destination.unlink(missing_ok=True)
            raise RuntimeError(f"Download failed for {token}: {exc}") from exc


def text_cell(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return str(first.get("text") or first.get("value") or "").strip()
        return str(first).strip()
    if isinstance(value, dict):
        return str(value.get("text") or value.get("value") or "").strip()
    return ""


def attachment_token(value: object) -> str:
    if isinstance(value, list) and value and isinstance(value[0], dict):
        item = value[0]
        return str(item.get("attachmentToken") or item.get("file_token") or item.get("token") or "")
    return ""


def normalize(value: object) -> object:
    if isinstance(value, dict):
        return {key: normalize(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def flatten_differences(left: object, right: object, path: str = "$") -> list[dict[str, object]]:
    if isinstance(left, dict) and isinstance(right, dict):
        rows: list[dict[str, object]] = []
        for key in sorted(set(left) | set(right)):
            child = f"{path}.{key}"
            if key not in left:
                rows.append({"path": child, "kind": "missing_left", "feishu": None, "local": right[key]})
            elif key not in right:
                rows.append({"path": child, "kind": "missing_right", "feishu": left[key], "local": None})
            else:
                rows.extend(flatten_differences(left[key], right[key], child))
        return rows
    if isinstance(left, list) and isinstance(right, list):
        rows = []
        for index in range(max(len(left), len(right))):
            child = f"{path}[{index}]"
            if index >= len(left):
                rows.append({"path": child, "kind": "missing_left", "feishu": None, "local": right[index]})
            elif index >= len(right):
                rows.append({"path": child, "kind": "missing_right", "feishu": left[index], "local": None})
            else:
                rows.extend(flatten_differences(left[index], right[index], child))
        return rows
    if left != right:
        return [{"path": path, "kind": "value", "feishu": left, "local": right}]
    return []


def overlap_differences(left: object, right: object, path: str = "$") -> list[dict[str, object]]:
    """Compare only overlapping fields; local-only and Feishu-only fields are ignored."""
    if is_nil(left) or is_nil(right):
        return []
    if isinstance(left, dict) and isinstance(right, dict):
        rows: list[dict[str, object]] = []
        for key in sorted(set(left) & set(right)):
            if path == "$" and key in METADATA_KEYS:
                continue
            rows.extend(overlap_differences(left[key], right[key], f"{path}.{key}"))
        return rows
    if isinstance(left, list) and isinstance(right, list):
        rows: list[dict[str, object]] = []
        for index in range(max(len(left), len(right))):
            child = f"{path}[{index}]"
            if index >= len(left):
                if not is_nil(right[index]):
                    rows.append({"path": child, "kind": "value", "feishu": None, "local": right[index]})
            elif index >= len(right):
                if not is_nil(left[index]):
                    rows.append({"path": child, "kind": "value", "feishu": left[index], "local": None})
            else:
                rows.extend(overlap_differences(left[index], right[index], child))
        return rows
    if left != right:
        return [{"path": path, "kind": "value", "feishu": left, "local": right}]
    return []


def local_index(root: Path, extensions: tuple[str, ...]) -> dict[tuple[str, str], list[tuple[Path, str]]]:
    result: dict[tuple[str, str], list[tuple[Path, str]]] = {}
    for extension in extensions:
        for path in root.rglob(f"*{extension}"):
            parts = path.relative_to(root).parts
            if len(parts) < 4:
                continue
            pi_code, model = parts[-3], parts[-2]
            vendor, material = parts[-5], parts[-4]
            product_name = material if vendor.casefold() == "polymaker" else f"{vendor} {material}"
            result.setdefault((pi_code.casefold(), printer_model(model)), []).append((path, product_name))
    return result


def parse_ini(text: str) -> dict[str, str]:
    """Parse the flat key=value format emitted by PrusaSlicer."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")):
            continue
        if "=" not in line:
            raise ValueError(f"invalid INI line: {line!r}")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"empty INI key: {line!r}")
        values[key] = value.strip()
    return values


def parse_downloaded_preset(text: str, slicer: str) -> object:
    if slicer.casefold() == "prusaslicer":
        return parse_ini(text)
    return json.loads(text)


def preset_extensions(slicer: str) -> tuple[str, ...]:
    return (".ini",) if slicer.casefold() == "prusaslicer" else (".json",)


def printer_model(printer: str) -> str:
    """Return a stable model key across display-name variants.

    Remove common vendor prefixes and nozzle suffixes because local export
    directories usually contain only the model, e.g. ``K2Pro`` or ``P2S``.
    """
    value = name_key(printer)
    for prefix in ("bambulab", "bbl", "creality", "elegoo", "qidi", "prusa", "snapmaker", "anycubic", "flashforge", "bambu"):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    return re.sub(r"(?:02|04|06|08)nozzle$", "", value)


def name_key(value: str) -> str:
    """Normalize human-facing names for matching, not for display.

    For example, ``Creality K2 Pro`` and ``K2Pro`` both become ``k2pro``.
    """
    return re.sub(r"[^a-z0-9]+", "", value.casefold()) if value else ""


def product_key(value: str) -> str:
    """Make Feishu product names comparable to local directory names."""
    value = value.casefold().replace("™", "").replace("®", "")
    return re.sub(r"[^a-z0-9]+", "", value)


def is_nil(value: object) -> bool:
    return isinstance(value, str) and value.casefold() == "nil"


def safe_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def write_reports(output: Path, results: list[dict]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "comparison.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output / "differences.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["preset_key", "pi_code", "printer", "local_file", "path", "kind", "feishu", "local"])
        writer.writeheader()
        for result in results:
            for diff in result["differences"]:
                writer.writerow({
                    "preset_key": result["preset_key"], "pi_code": result["pi_code"],
                    "printer": result["printer"], "local_file": result.get("local_file", ""),
                    "path": diff["path"], "kind": diff["kind"],
                    "feishu": safe_json(diff["feishu"]), "local": safe_json(diff["local"]),
                })
    rows = [
        "<!doctype html><meta charset='utf-8'><title>Preset comparison</title>",
        "<style>body{font:14px system-ui;margin:24px} table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:6px;text-align:left;vertical-align:top}th{background:#eee}.ok{color:green}.bad{color:#b00}pre{margin:0;white-space:pre-wrap}</style>",
        f"<h1>Preset comparison</h1><p>{len(results)} Feishu records compared.</p>",
        "<table><tr><th>Preset</th><th>Status</th><th>Differences</th></tr>",
    ]
    for result in results:
        status = result["status"]
        rows.append(f"<tr><td>{html.escape(result['preset_key'])}</td><td class='{('ok' if status == 'same' else 'bad')}'>{html.escape(status)}</td><td>")
        if result["differences"]:
            rows.append("<table><tr><th>Path</th><th>Kind</th><th>Feishu</th><th>Local</th></tr>")
            for diff in result["differences"]:
                rows.append("<tr>" + "".join(f"<td><pre>{html.escape(safe_json(value))}</pre></td>" for value in (diff["path"], diff["kind"], diff["feishu"], diff["local"])) + "</tr>")
            rows.append("</table>")
        rows.append("</td></tr>")
    rows.append("</table>")
    (output / "comparison.html").write_text("".join(rows), encoding="utf-8")


def write_summary_report(output: Path, summaries: dict[str, dict]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    statuses = ("different", "local_match_ambiguous", "local_missing", "same")
    totals = {
        status: sum(result["summary"].get(status, 0) for result in summaries.values())
        for status in statuses
    }
    rows = [
        "<!doctype html><meta charset='utf-8'><title>Preset comparison summary</title>",
        "<style>body{font:14px system-ui;margin:24px} table{border-collapse:collapse;width:100%;margin-bottom:24px}th,td{border:1px solid #ccc;padding:8px 16px;text-align:right}th:first-child,td:first-child{text-align:left}th{background:#eee}.different{color:#b00;font-weight:600}.ambiguous{color:#b36b00;font-weight:600}.missing{color:#666;font-weight:600}.same{color:green;font-weight:600}.ok{color:green}.bad{color:#b00}section{margin-top:32px}section table{margin-bottom:0}</style>",
        "<h1>Preset comparison summary</h1>",
        "<table><tr><th>Slicer</th><th>Different</th><th>Local match ambiguous</th><th>Local missing</th><th>Same</th></tr>",
    ]
    for slicer, result in summaries.items():
        counts = result["summary"]
        rows.append(
            "<tr>"
            f"<td>{html.escape(slicer)}</td>"
            f"<td class='different'>{counts.get('different', 0)}</td>"
            f"<td class='ambiguous'>{counts.get('local_match_ambiguous', 0)}</td>"
            f"<td class='missing'>{counts.get('local_missing', 0)}</td>"
            f"<td class='same'>{counts.get('same', 0)}</td>"
            "</tr>"
        )
    rows.append(
        "<tr><th>Total</th>"
        + "<th class='different'>"
        + str(totals["different"])
        + "</th><th class='ambiguous'>"
        + str(totals["local_match_ambiguous"])
        + "</th><th class='missing'>"
        + str(totals["local_missing"])
        + "</th><th class='same'>"
        + str(totals["same"])
        + "</th>"
        + "</tr>"
    )
    rows.append("</table>")
    for slicer, result in summaries.items():
        detail_path = Path(result["output"]) / "comparison.html"
        detail = detail_path.read_text(encoding="utf-8")
        detail = re.sub(
            r"(?is)<!doctype html>|<meta[^>]*>|<title>.*?</title>|<style>.*?</style>",
            "",
            detail,
        ).strip()
        rows.append(f"<section><h2>{html.escape(slicer)}</h2>{detail}</section>")
    output.write_text("".join(rows), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=Path(r"C:\Users\zhengyang\Documents\GitHub\preset-worker\.env"))
    parser.add_argument("--local-root", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--preset-table", default=DEFAULT_PRESET_TABLE)
    parser.add_argument("--mapping-table", default=DEFAULT_MAPPING_TABLE)
    parser.add_argument("--slicer", default=None, help="Only compare this slicer (default: all slicers)")
    args = parser.parse_args()

    client = FeishuClient(load_env(args.env))
    mappings = {}
    for record in client.records(args.mapping_table):
        fields = record.get("fields", {})
        code = text_cell(fields.get("PI Code"))
        product = text_cell(fields.get("Product Name"))
        if code:
            mappings[code.casefold()] = product

    records = client.records(args.preset_table)
    slicers = [args.slicer] if args.slicer else list(DEFAULT_SLICERS)
    summaries: dict[str, dict] = {}

    for slicer_name in slicers:
        output = (
            args.output
            if args.output and args.slicer
            else (args.output or Path("reports")) / f"comparison-{slicer_name}"
        )
        local_root = args.local_root or DEFAULT_LOCAL_ROOTS.get(
            slicer_name.casefold(), DEFAULT_LOCAL_ROOTS["bambustudio"]
        )
        index = local_index(local_root, preset_extensions(slicer_name))
        download_dir = output / "feishu"
        download_dir.mkdir(parents=True, exist_ok=True)
        results: list[dict] = []
        slicer_names = {slicer_name.casefold()}
        slicer_names.update(name.casefold() for name in FEISHU_SLICER_NAMES.get(slicer_name, ()))
        for record in records:
            fields = record.get("fields", {})
            preset_key = text_cell(fields.get("preset_key"))
            pi_code = text_cell(fields.get("pi_code"))
            printer = text_cell(fields.get("printer"))
            slicer = text_cell(fields.get("slicer"))
            if slicer.casefold() not in slicer_names:
                continue
            item = {"preset_key": preset_key, "pi_code": pi_code, "printer": printer, "product_name": mappings.get(pi_code.casefold(), ""), "differences": []}
            token = attachment_token(fields.get("preset data"))
            if not token:
                item["status"] = "missing_feishu_attachment"
                results.append(item)
                continue
            downloaded = download_dir / f"{record.get('record_id', 'unknown')}.json"
            if not downloaded.exists():
                client.download_attachment(token, downloaded)
            try:
                feishu_data = parse_downloaded_preset(downloaded.read_text(encoding="utf-8"), slicer_name)
            except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
                item["status"] = "invalid_feishu_json"
                item["error"] = str(exc)
                results.append(item)
                continue
            candidates = index.get((pi_code.casefold(), printer_model(printer)), [])
            expected_product = product_key(mappings.get(pi_code.casefold(), ""))
            if expected_product:
                exact_product = [item for item in candidates if product_key(item[1]) == expected_product]
                if exact_product:
                    candidates = exact_product
            if len(candidates) != 1:
                item["status"] = "local_match_ambiguous" if candidates else "local_missing"
                item["candidate_files"] = [str(path) for path, _product in candidates]
                results.append(item)
                continue
            local_path = candidates[0][0]
            item["local_file"] = str(local_path)
            local_data = parse_downloaded_preset(local_path.read_text(encoding="utf-8"), slicer_name)
            all_diffs = overlap_differences(normalize(feishu_data), normalize(local_data))
            item["differences"] = all_diffs
            item["parameter_differences"] = all_diffs
            item["status"] = "same" if not all_diffs else "different"
            results.append(item)

        write_reports(output, results)
        summary = {status: sum(1 for item in results if item["status"] == status) for status in sorted({item["status"] for item in results})}
        summaries[slicer_name] = {"records": len(results), "summary": summary, "output": str(output)}

    summary_output = (
        args.output.parent / "comparison-summary.html"
        if args.output and args.slicer
        else (args.output or Path("reports")) / "comparison-summary.html"
    )
    write_summary_report(summary_output, summaries)
    print(json.dumps({"slicers": summaries, "summary_html": str(summary_output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
