"""Download attachments in the preset data and 3MF fields of a Feishu table.

The table is read from ``FEISHU_TABLE_ID`` in the selected .env file.  The
command is read-only against Feishu and writes attachments to the output
directory using ``<record_id>_<original_name>`` filenames.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


AUTH_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
BITABLE_API = "https://open.feishu.cn/open-apis/bitable/v1"
MEDIA_URL = "https://open.feishu.cn/open-apis/drive/v1/medias/{}/download"
ATTACHMENT_FIELDS = ("preset data", "3mf", "preset 3mf")


def log(message: str, *, error: bool = False) -> None:
    """Print a timestamped log message."""
    stream = sys.stderr if error else sys.stdout
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    print(f"[{timestamp}] {message}", file=stream)


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RuntimeError(f"Unable to read .env file: {path}: {exc}") from exc

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def api_json(url: str, *, token: str | None = None, payload: dict | None = None) -> dict:
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


def required(env: dict[str, str], *keys: str) -> list[str]:
    missing = [key for key in keys if not env.get(key)]
    if missing:
        raise RuntimeError(f"Missing .env values: {', '.join(missing)}")
    return [env[key] for key in keys]


def get_records(env: dict[str, str]) -> tuple[str, list[dict]]:
    app_id, app_secret, app_token, table_id = required(
        env, "FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_APP_TOKEN", "FEISHU_TABLE_ID"
    )
    auth = api_json(
        AUTH_URL,
        payload={"app_id": app_id, "app_secret": app_secret},
    )
    token = auth["tenant_access_token"]

    records: list[dict] = []
    page_token = ""
    while True:
        query = {"page_size": "100"}
        if page_token:
            query["page_token"] = page_token
        url = f"{BITABLE_API}/apps/{app_token}/tables/{table_id}/records?{urlencode(query)}"
        data = api_json(url, token=token).get("data", {})
        records.extend(data.get("items", []))
        if not data.get("has_more"):
            return token, records
        page_token = data.get("page_token", "")
        if not page_token:
            raise RuntimeError("Feishu pagination response has no page_token")


def attachment_list(value: object) -> list[dict]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if isinstance(value, dict):
        value = [value]
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def safe_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return cleaned or "attachment"


def download(url: str, token: str, destination: Path) -> None:
    request = Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urlopen(request, timeout=120) as response, destination.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
    except HTTPError as exc:
        destination.unlink(missing_ok=True)
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Download failed: HTTP {exc.code}: {detail or exc.reason}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"Download failed: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument("--output", type=Path, default=Path("downloads/preset_data"))
    parser.add_argument("--force", action="store_true", help="overwrite existing files")
    args = parser.parse_args()

    try:
        token, records = get_records(load_env(args.env))
        args.output.mkdir(parents=True, exist_ok=True)
        downloaded = skipped = 0
        for record in records:
            record_id = str(record.get("record_id") or "unknown")
            fields = record.get("fields", {})
            for field_name in ATTACHMENT_FIELDS:
                attachments = attachment_list(fields.get(field_name))
                field_slug = safe_name(field_name.replace(" ", "_"))
                for index, attachment in enumerate(attachments, start=1):
                    # Feishu may return attachment fields using either the
                    # newer camelCase token or legacy file_token/token names.
                    file_token = (
                        attachment.get("attachmentToken")
                        or attachment.get("file_token")
                        or attachment.get("token")
                    )
                    url = attachment.get("url") or attachment.get("tmp_url")
                    if not url and file_token:
                        url = MEDIA_URL.format(file_token)
                    if not url:
                        log(
                            f"Skipping {record_id} field {field_name} attachment {index}: missing URL/token",
                            error=True,
                        )
                        continue

                    filename = safe_name(str(attachment.get("name") or f"attachment_{index}"))
                    destination = args.output / f"{safe_name(record_id)}_{field_slug}_{filename}"
                    if destination.exists() and not args.force:
                        skipped += 1
                        log(f"Skipping existing file: {destination}")
                        continue
                    log(f"Downloading {record_id} field {field_name} attachment {index}: {destination}")
                    download(url, token, destination)
                    downloaded += 1
                    log(f"Downloaded {record_id} field {field_name} attachment {index}: {destination}")

        log(f"Completed: {len(records)} records, {downloaded} downloaded, {skipped} skipped")
        return 0
    except (KeyError, RuntimeError) as exc:
        log(f"Error: {exc}", error=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
