# P10-A Baseline

审计基线：提交 `b7e0b26f028dab25d9571712024a50a8da5dd57a`；审计日期 2026-11-10。工作区原有未跟踪文件 `docs/p10-a.md`，本审计未修改。

## Repository

- Python package 在 `src/preset_worker/`，测试在 `tests/`，fixture 在 `tests/fixtures/slicers/`。
- 构建由 `pyproject.toml` 的 setuptools 驱动；`requires-python = ">=3.10"`；项目运行时依赖声明为空。
- CLI：`preset-worker = preset_worker.cli:main`，另有 `coverage-sync`。
- runtime：`preset_worker.runtime.WorkerRuntime` 串行轮询 `PREVIEW_REQUESTED`、`VALIDATING`、`APPROVING`。
- package 版本：`src/preset_worker/__init__.py:3` 为 `0.3.1`。

实际支持的业务标识（`slicers/registry.py:28-36`）：`BambuStudio`、`OrcaSlicer`、`CrealityPrint`、`ElegooSlicer`、`PrusaSlicer`、`SnapmakerOrcaSlicer`。别名另见 `slicers/contracts.py:98-113` 和 `registry.py:19-25`。

Fixture 目录：Creality、Elegoo、Orca、SnapmakerOrca、Prusa；Bambu 的若干集成测试依赖仓库外/未提交的 `downloads/3mf-fixture`。

## Environment and tests

- `python --version`：Python 3.12.10；满足项目下限。
- `python -m pytest -q`：无法执行，环境没有 pytest（`No module named pytest`）。
- `PYTHONPATH=src; python -m unittest discover -s tests -p 'test*.py'`：240 tests，`FAILED (failures=6, errors=8, skipped=2)`。
- 8 个 errors 主要是 `downloads/3mf-fixture/PPS100CF10 H2D (1).*` 不存在；2 个 skipped 是可选真实 fixture 不存在。
- 6 个 failures：5 个 fixture 重要参数分类失败，1 个 Prusa `MISSING_IN_PRESET` 期望失败。详见 `08-fixtures-and-tests.md`。

证据等级：本文件中的版本、入口和支持列表均 `CONFIRMED`；未执行 pytest 的原因 `CONFIRMED`；依赖外部下载目录的完整集成覆盖 `NOT_VERIFIED`。
