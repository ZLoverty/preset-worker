"""Read all records from the Feishu submission table.

The script intentionally uses only Python's standard library.  By default it
reads the .env file used by preset-worker, but another file can be supplied
with --env.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_ENV_FILE = Path(r"C:\Users\zhengyang\Documents\GitHub\preset-worker\.env")
AUTH_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
BITABLE_API = "https://open.feishu.cn/open-apis/bitable/v1"


def load_env(path: Path) -> dict[str, str]:
    """Load simple KEY=VALUE entries from a dotenv file."""
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


def require_config(env: dict[str, str], *keys: str) -> list[str]:
    missing = [key for key in keys if not env.get(key)]
    if missing:
        raise RuntimeError(f".env 缺少配置: {', '.join(missing)}")
    return [env[key] for key in keys]


def request_json(url: str, *, method: str = "GET", payload: dict | None = None,
                 token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"请求飞书 API 失败: {exc}") from exc

    if result.get("code", 0) != 0:
        raise RuntimeError(
            f"飞书 API 返回错误 code={result.get('code')}: {result.get('msg', '未知错误')}"
        )
    return result


def get_tenant_token(app_id: str, app_secret: str) -> str:
    result = request_json(
        AUTH_URL,
        method="POST",
        payload={"app_id": app_id, "app_secret": app_secret},
    )
    return result["tenant_access_token"]


def read_submission_records(env: dict[str, str]) -> list[dict]:
    app_id, app_secret, app_token, table_id = require_config(
        env,
        "FEISHU_APP_ID",
        "FEISHU_APP_SECRET",
        "FEISHU_APP_TOKEN",
        "FEISHU_SUBMISSION_TABLE_ID",
    )
    tenant_token = get_tenant_token(app_id, app_secret)

    records: list[dict] = []
    page_token: str | None = None
    while True:
        query = {"page_size": "100"}
        if page_token:
            query["page_token"] = page_token
        url = (
            f"{BITABLE_API}/apps/{app_token}/tables/{table_id}/records?"
            f"{urlencode(query)}"
        )
        data = request_json(url, token=tenant_token).get("data", {})
        records.extend(data.get("items", []))
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
        if not page_token:
            raise RuntimeError("飞书 API 表示还有下一页，但没有返回 page_token")
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="读取飞书 submission table 的全部记录")
    parser.add_argument(
        "--env",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help=f".env 文件路径（默认: {DEFAULT_ENV_FILE}）",
    )
    args = parser.parse_args()

    try:
        records = read_submission_records(load_env(args.env))
    except (KeyError, RuntimeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1

    json.dump(records, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
