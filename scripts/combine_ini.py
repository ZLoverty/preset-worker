
from pathlib import Path
import configparser
import argparse
import io
import sys

PRESET_TYPE = "filament"
ENCODING = "utf-8-sig"


def read_ini(path):
    """读取 INI，支持无 section 的独立 preset。"""
    text = path.read_text(encoding=ENCODING)

    config = configparser.RawConfigParser(
        interpolation=None,
        strict=True,
        delimiters=("=",),
        comment_prefixes=("#", ";"),
    )
    config.optionxform = str

    # 判断是否已有 section
    has_section = any(
        line.strip().startswith("[")
        and line.strip().endswith("]")
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", ";"))
    )

    if has_section:
        config.read_string(text)
        return config

    # 无 section 的 INI 一律按 filament preset 处理
    section = f"{PRESET_TYPE}:{path.stem}"
    config.read_string(f"[{section}]\n{text}")
    return config


def merge_presets(input_dir, output):
    input_dir = Path(input_dir).resolve()
    output = Path(output).resolve()

    if not input_dir.is_dir():
        raise NotADirectoryError(input_dir)

    bundle = configparser.RawConfigParser(
        interpolation=None,
        strict=True,
        delimiters=("=",),
    )
    bundle.optionxform = str

    files = sorted(
        p for p in input_dir.rglob("*")
        if p.is_file()
        and p.suffix.lower() == ".ini"
        and p.resolve() != output
    )

    stats = {
        "files": len(files),
        "presets": 0,
        "duplicates": [],
        "errors": [],
    }

    for path in files:
        try:
            config = read_ini(path)
        except (ValueError, OSError, configparser.Error) as exc:
            stats["errors"].append((str(path), str(exc)))
            continue

        for section in config.sections():
            preset_type = section.split(":", 1)[0]

            if preset_type != PRESET_TYPE:
                continue

            if bundle.has_section(section):
                stats["duplicates"].append((str(path), section))
                continue

            bundle.add_section(section)

            for key, value in config.items(section):
                bundle.set(section, key, value)

            stats["presets"] += 1

    # 有重复或解析错误时，不输出不完整的 Bundle
    if stats["duplicates"] or stats["errors"]:
        print("\n发现问题，未生成 Bundle。")

        for path, section in stats["duplicates"]:
            print(f"[重复] {section}: {path}")

        for path, error in stats["errors"]:
            print(f"[错误] {path}: {error}")

        return False

    if stats["presets"] == 0:
        print("没有找到有效的 preset。")
        return False

    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", encoding="utf-8") as f:
        bundle.write(f, space_around_delimiters=True)

    print(f"\n扫描 INI 文件: {stats['files']}")
    print(f"合并 preset: {stats['presets']}")
    print(f"输出文件: {output}")

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="递归合并 PrusaSlicer INI presets"
    )
    parser.add_argument("input_dir", help="输入文件夹")
    parser.add_argument(
        "-o", "--output",
        default="config_bundle.ini",
        help="输出 Bundle 文件路径",
    )
    args = parser.parse_args()

    success = merge_presets(args.input_dir, args.output)
    sys.exit(0 if success else 1)
