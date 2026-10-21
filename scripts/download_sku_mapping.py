"""Download and analyze the PI Code -> Product Name mapping from Feishu SKU table.

The command is read-only against Feishu. It writes a raw record snapshot and
derived mapping reports under ``reports/sku-mapping`` by default. By default,
only ``polymaker`` records are included by default.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


AUTH_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
BITABLE_API = "https://open.feishu.cn/open-apis/bitable/v1"


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


class FeishuClient:
    def __init__(self, env: dict[str, str]) -> None:
        required = ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_APP_TOKEN", "FEISHU_SKU_TABLE_ID")
        missing = [key for key in required if not env.get(key)]
        if missing:
            raise RuntimeError(f"Missing .env values: {', '.join(missing)}")
        auth = api_json(
            AUTH_URL,
            payload={"app_id": env["FEISHU_APP_ID"], "app_secret": env["FEISHU_APP_SECRET"]},
        )
        self.token = auth["tenant_access_token"]
        self.app_token = env["FEISHU_APP_TOKEN"]
        self.table_id = env["FEISHU_SKU_TABLE_ID"]

    def records(self) -> list[dict]:
        records: list[dict] = []
        page_token = ""
        while True:
            query = {"page_size": "100"}
            if page_token:
                query["page_token"] = page_token
            data = api_json(
                f"{BITABLE_API}/apps/{self.app_token}/tables/{self.table_id}/records?{urlencode(query)}",
                token=self.token,
            ).get("data", {})
            records.extend(data.get("items", []))
            if not data.get("has_more"):
                return records
            page_token = data.get("page_token", "")
            if not page_token:
                raise RuntimeError("Feishu pagination response has no page_token")


def cell_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value).strip()
    if isinstance(value, list):
        return "".join(cell_text(item) for item in value).strip()
    if isinstance(value, dict):
        return str(value.get("text") or value.get("value") or value.get("name") or "").strip()
    return ""


def normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def derive(records: list[dict]) -> tuple[list[dict[str, object]], dict[str, object]]:
    rows: list[dict[str, object]] = []
    by_pi: dict[str, set[str]] = defaultdict(set)
    by_product: dict[str, set[str]] = defaultdict(set)
    empty_pi = empty_product = 0

    for record in records:
        fields = record.get("fields", {})
        brand = cell_text(fields.get("Brand Record"))
        pi_code = cell_text(fields.get("PI Code"))
        product_name = cell_text(fields.get("Product Name"))
        if not pi_code:
            empty_pi += 1
        if not product_name:
            empty_product += 1
        pi_key, product_key = normalize_key(pi_code), normalize_key(product_name)
        if pi_key:
            by_pi[pi_key].add(product_name)
        if product_key:
            by_product[product_key].add(pi_code)
        rows.append({
            "record_id": record.get("record_id", ""),
            "brand_record": brand,
            "pi_code": pi_code,
            "product_name": product_name,
        })

    duplicate_rows = [row for row in rows if row["pi_code"] and len(by_pi[normalize_key(str(row["pi_code"]))]) > 1]
    summary = {
        "records": len(rows),
        "brand_counts": dict(sorted(Counter(str(row["brand_record"]) for row in rows).items())),
        "non_empty_pi_codes": len(by_pi),
        "non_empty_product_names": len(by_product),
        "empty_pi_code_records": empty_pi,
        "empty_product_name_records": empty_product,
        "one_to_one_pi_codes": sum(len(products) == 1 for products in by_pi.values()),
        "one_to_many_pi_codes": sum(len(products) > 1 for products in by_pi.values()),
        "many_to_one_product_names": sum(len(codes) > 1 for codes in by_product.values()),
        "ambiguous_rows": len(duplicate_rows),
        "pi_to_products": {key: sorted(values) for key, values in sorted(by_pi.items())},
        "product_to_pi_codes": {key: sorted(values) for key, values in sorted(by_product.items())},
    }
    return rows, summary


def write_outputs(output: Path, raw_records: list[dict], rows: list[dict[str, object]], summary: dict[str, object]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "raw_records.json").write_text(json.dumps(raw_records, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "analysis.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output / "mapping.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["record_id", "brand_record", "pi_code", "product_name"])
        writer.writeheader()
        writer.writerows(rows)

    lines = ["# SKU mapping analysis", "", f"- Records: {summary['records']}", f"- Brands: {summary['brand_counts']}", f"- Unique PI Codes: {summary['non_empty_pi_codes']}", f"- Unique Product Names: {summary['non_empty_product_names']}", f"- One-to-one PI Codes: {summary['one_to_one_pi_codes']}", f"- One-to-many PI Codes: {summary['one_to_many_pi_codes']}", f"- Many-to-one Product Names: {summary['many_to_one_product_names']}", f"- Empty PI Code records: {summary['empty_pi_code_records']}", f"- Empty Product Name records: {summary['empty_product_name_records']}", "", "## PI Code -> Product Name", ""]
    for pi_code, products in summary["pi_to_products"].items():
        lines.append(f"- `{pi_code}` -> {', '.join(products) if products else '(empty)'}")
    (output / "analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=Path(r"C:\Users\zhengyang\Documents\GitHub\preset-worker\.env"))
    parser.add_argument("--output", type=Path, default=Path("reports/sku-mapping"))
    parser.add_argument("--brands", nargs="+", default=["polymaker"], help="Brand Record values to include")
    args = parser.parse_args()
    client = FeishuClient(load_env(args.env))
    all_records = client.records()
    allowed_brands = {normalize_key(brand) for brand in args.brands}
    raw_records = [
        record for record in all_records
        if normalize_key(cell_text(record.get("fields", {}).get("Brand Record"))) in allowed_brands
    ]
    rows, summary = derive(raw_records)
    write_outputs(args.output, raw_records, rows, summary)
    print(json.dumps({key: value for key, value in summary.items() if key not in {"pi_to_products", "product_to_pi_codes"}}, ensure_ascii=False, indent=2))
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
