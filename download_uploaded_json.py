"""Download attachments from the uploaded_json field in the submission table."""

from __future__ import annotations

import argparse
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


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RuntimeError(f"无法读取 .env 文件: {path}\n{exc}") from exc
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


def require(env: dict[str, str], *keys: str) -> list[str]:
    missing = [key for key in keys if not env.get(key)]
    if missing:
        raise RuntimeError(f".env 缺少配置: {', '.join(missing)}")
    return [env[key] for key in keys]


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
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"请求飞书 API 失败: {exc}") from exc
    if result.get("code", 0) != 0:
        raise RuntimeError(f"飞书 API 错误 {result.get('code')}: {result.get('msg')}")
    return result


def get_records(env: dict[str, str]) -> tuple[str, str, list[dict]]:
    app_id, app_secret, app_token, table_id = require(
        env,
        "FEISHU_APP_ID",
        "FEISHU_APP_SECRET",
        "FEISHU_APP_TOKEN",
        "FEISHU_SUBMISSION_TABLE_ID",
    )
    token = api_json(AUTH_URL, payload={"app_id": app_id, "app_secret": app_secret})[
        "tenant_access_token"
    ]
    records: list[dict] = []
    page_token = ""
    while True:
        query = {"page_size": "100"}
        if page_token:
            query["page_token"] = page_token
        url = f"{BITABLE_API}/apps/{app_token}/tables/{table_id}/records?{urlencode(query)}"
        data = api_json(url, token).get("data", {})
        records.extend(data.get("items", []))
        if not data.get("has_more"):
            return token, app_token, records
        page_token = data.get("page_token", "")
        if not page_token:
            raise RuntimeError("分页响应缺少 page_token")


def attachment_list(value: object) -> list[dict]:
    """Normalize a cell value into a list of attachment dictionaries."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if isinstance(value, dict):
        value = [value]
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def safe_name(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return name or "attachment"


def download(url: str, token: str, destination: Path) -> None:
    request = Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urlopen(request, timeout=120) as response, destination.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"下载失败: HTTP {exc.code}: {detail or exc.reason}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"下载失败: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="下载 submission table 的 uploaded_json 附件")
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument("--output", type=Path, default=Path("downloads/uploaded_json"))
    parser.add_argument("--force", action="store_true", help="覆盖已存在的文件")
    args = parser.parse_args()

    try:
        env = load_env(args.env)
        token, _app_token, records = get_records(env)
        args.output.mkdir(parents=True, exist_ok=True)
        downloaded = 0
        for record in records:
            record_id = record.get("record_id", "unknown")
            attachments = attachment_list(record.get("fields", {}).get("uploaded_json"))
            for index, attachment in enumerate(attachments, start=1):
                file_token = attachment.get("file_token") or attachment.get("token")
                url = attachment.get("url") or attachment.get("tmp_url")
                # Bitable returns a ready-to-use URL.  Prefer it because it
                # may contain attachment-specific routing information.
                if not url and file_token:
                    url = MEDIA_URL.format(file_token)
                if not url:
                    print(f"跳过 {record_id}: 附件没有 file_token 或 url", file=sys.stderr)
                    continue
                filename = safe_name(attachment.get("name") or f"attachment_{index}")
                destination = args.output / f"{record_id}_{filename}"
                if destination.exists() and not args.force:
                    print(f"跳过已存在: {destination}")
                    continue
                download(url, token, destination)
                downloaded += 1
                print(f"已下载: {destination}")
        print(f"完成：读取 {len(records)} 条记录，下载 {downloaded} 个附件。")
        return 0
    except (KeyError, RuntimeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
