# P9-C 多切片器 3MF 兼容性调研报告

## 结论摘要

当前可以确认的只有 Bambu Studio 风格项目：仓库中有真实 3MF 配对样本，包含 `Metadata/project_settings.config`，八个目标参数可以被现有 P9-B2 解析器读取。其余五个支持的 Preset 切片器都缺少真实的“切片器导出 3MF + 对应 Preset”配对样本，因此目前不能宣称 3MF 一致性兼容。

建议暂不修改 Preview，也不要把其他 slicer 路由到 Bambu validator。P9-D 应先补充真实配对夹具，再按 OrcaSlicer、Snapmaker OrcaSlicer、ElegooSlicer/CrealityPrint、PrusaSlicer 的顺序推进。

## 1. 已审计的 Worker 实现

| 层次 | 文件 | 实际职责 |
|---|---|---|
| Worker 调度 | `src/preset_worker/runtime.py` | 发现 `PREVIEW_REQUESTED`，调用 `PreviewService`；没有按 slicer 增加 Preview 分支 |
| Native Preset 处理 | `src/preset_worker/services/enrichment.py` | 下载 `preset data`/`uploaded_json`，按 `slicer` 从 registry 取处理器，完成 parse、validate、normalize、policy、serialize、diff |
| 处理器契约 | `src/preset_worker/slicers/contracts.py` | `Artifact`、`ProcessingContext`、`SlicerProcessor`、`ProcessedArtifact`；Artifact 对格式不做假设 |
| 注册表 | `src/preset_worker/slicers/registry.py` | 注册 BambuStudio、OrcaSlicer、SnapmakerOrcaSlicer、CrealityPrint、ElegooSlicer、PrusaSlicer |
| Preview 集成 | `src/preset_worker/services/preview.py` | 保留 `CandidateResult.source_artifact`，在 native Preview 写入前生成一致性文本 |
| 3MF 读取 | `src/preset_worker/three_mf/safe_zip.py` | ZIP 安全边界、路径和大小检查 |
| Bambu 提取 | `src/preset_worker/three_mf/bambu_parser.py` | 固定 Bambu 路径的 JSON/XML 读取、参数提取、filament slot、plate/object 上下文和数组解析 |
| Bambu 比较 | `src/preset_worker/three_mf/consistency.py` | Bambu Preset 解析/规范化、slot 选择、八参数逐元素比较、P9-B2 报告生成 |

当前 P9-B2 的主要边界是：`bambu_parser.py` 同时承担 ZIP 读取后的 Bambu 配置提取和部分上下文解析；`consistency.py` 又直接实例化 `BambuStudioProcessor` 并直接使用 Bambu 参数名。因此它不是通用 3MF 比较引擎。

已经分离的部分：

1. ZIP 安全读取与 slicer 配置抽取有明确文件边界。
2. native Preset 处理通过 `SlicerProcessor` 契约隔离。
3. slot 选择、参数值比较和报告拼装目前集中在 Bambu consistency 模块。

尚未分离的部分：

1. 3MF 中的配置路径和配置格式仍绑定 Bambu 项目结构。
2. Preset 规范化直接依赖 `BambuStudioProcessor`。
3. slot identity 选择逻辑直接读取 Bambu 的 `filament_settings_id`。
4. `runtime_effective_status` 依赖 Bambu 的 `resolve_bambu_project()`，不能直接套用其他 slicer。

## 2. 已有夹具与实验

### 真实项目 3MF

发现的真实或用户提供项目 3MF：

| 文件 | 观察结果 | 可否作为其他 slicer 证据 |
|---|---|---|
| `downloads/3mf-fixture/PPS100CF10 H2D (1).3mf` | Bambu 风格项目，含 project/model/slice/filament sequence 配置；有对应 JSON | Bambu：已验证 |
| `downloads/legacy_preset_data_audit/recvgKBtHJUrDm_1_PPS100CF10 H2D.3mf` | 与上面文件内容和大小一致的重复样本 | Bambu：重复证据，不是新 slicer |
| `preset-method/All in one Test.3mf` | Bambu 风格项目，含 97 个成员和项目配置；model XML 存在解析问题 | Bambu 格式参考，不是其他 slicer 证据 |
| `OrcaSlicer/tests/data/test_3mf/Geräte/Büchse.3mf` | 仅有 3D 模型结构，且安全 ZIP 检查发现路径穿越成员 | 几何/安全测试，不是配置项目 |
| `BambuStudio/tests/data/test_3mf/Geräte/Büchse.3mf` | 同类测试资源，非用户配置项目 | 几何/安全测试，不是配置项目 |

仓库和相关工作区中没有发现由 OrcaSlicer、Snapmaker OrcaSlicer、CrealityPrint、ElegooSlicer 或 PrusaSlicer 导出的真实项目 3MF 与 Preset 配对文件。现有各 slicer 目录中的 JSON/INI 都是 Preset 夹具，不是 3MF 项目夹具。

### Bambu fixture 的实际结构

`PPS100CF10 H2D (1).3mf` 的配置成员包括：

- `Metadata/project_settings.config`：JSON，大小约 64 KB；
- `Metadata/model_settings.config`：XML；
- `Metadata/slice_info.config`：XML；
- `Metadata/filament_sequence.json`：JSON；
- `Metadata/plate_*.json`：逐 plate 元数据；
- 大量模型文件和缩略图。

实际读取到：

```text
filament_settings_id              ["PPS100CF10 H2D"]
filament_flow_ratio               ["1", "0.96"]
filament_max_volumetric_speed     ["8", "3"]
nozzle_temperature                ["350", "320"]
nozzle_temperature_initial_layer  ["350", "320"]
fan_min_speed                     ["0"]
fan_max_speed                     ["30"]
fan_cooling_layer_time            ["20"]
slow_down_layer_time              ["6"]
```

对应 JSON Preset 经过现有 P9-B2 validator 的结果为：slot `UNIQUE`、slot id `1`；八个参数中两个 `MATCH`，六个因 Preset 缺少对应参数而为 `MISSING_IN_PRESET`。这证明当前 Bambu 逻辑能产生逐项结果，但不证明其他 slicer 的 3MF 结构可复用。

`preset-method/All in one Test.3mf` 也包含八个参数和一个 `Generic PLA` slot，但 `model_settings.config` 的 XML 解析报错；它可作为 Bambu 风格容错样本，不能作为干净的验收 fixture。

### 源码交叉证据

本地 OrcaSlicer 源码明确使用 Bambu 风格路径：

- `src/libslic3r/Format/bbs_3mf.cpp` 定义 `Metadata/project_settings.config`、`Metadata/model_settings.config` 和 `Metadata/filament_sequence.json`；
- Orca 的 `filament_settings_id` 是多值配置；
- `filament_sequence` 在文件中按 1-based 存储，读取时转成 0-based；
- Orca 的导出流程明确称为 BBL 3MF。

这支持“Orca 可能复用 Bambu 3MF 读取器”的假设，但没有真实 Orca 导出样本，故不能升级为已验证兼容。

## 3. 各 slicer 结论

### BambuStudio — `VERIFIED_FOR_CURRENT_FIXTURE`

- 有真实 Preset + 3MF 配对样本。
- 3MF 配置路径和数据格式已确认。
- `filament_settings_id` 可将 Preset 与唯一 slot 对上。
- 多 filament 数组按 slot 数量和 1-based slot id 解析。
- 仍需注意：某些参数是存储值，不等于最终 G-code runtime-effective 值。

### OrcaSlicer — `INSUFFICIENT_EVIDENCE`, `REUSE_WITH_ADAPTER` 候选

- Preset 是 JSON，现有处理器已单独注册；部分目标参数在 Preset 夹具中出现。
- 本地 Orca 源码使用 BBL 3MF 配置路径和类似的 `filament_settings_id`/filament sequence 机制。
- 没有实际 Orca 导出 3MF 与对应 Preset，未验证 Save Project、Export 3MF、gcode.3mf 的差异。
- 不能直接把 `BambuStudio` slicer id 改成 Orca，也不能假定所有 Orca 3MF 都含 Bambu 配置。

### SnapmakerOrcaSlicer — `INSUFFICIENT_EVIDENCE`, 独立验证

- Preset JSON 结构接近 Orca，但 `inherits` 和版本体现 Snapmaker fork 语义。
- 现有代码已使用独立 `SnapmakerOrcaSlicerProcessor`，说明业务 identity 不应合并。
- 没有 Snapmaker 导出 3MF；不应因 JSON Preset 兼容或 upstream cross-import 就宣称 3MF 兼容。

### CrealityPrint — `INSUFFICIENT_EVIDENCE`, `SEPARATE_PARSER_REQUIRED` 候选

- Preset 是 plain JSON，现有夹具只证明 Preset import/export 和参数保存。
- 没有 CrealityPrint 项目 3MF；无法确认是否保存项目配置、是否保存 slot、是否使用不同路径或私有结构。
- `base_id` 等 identity 字段已有 round-trip 归一化证据，不能直接映射成 3MF filament identity。

### ElegooSlicer — `INSUFFICIENT_EVIDENCE`, `SEPARATE_PARSER_REQUIRED` 候选

- Preset 是 plain JSON；现有夹具只证明 Preset round-trip。
- 没有 ElegooSlicer 项目 3MF。
- 不能因为 JSON 里出现同名参数，就假定项目配置包含这些参数或语义相同。

### PrusaSlicer — `INSUFFICIENT_EVIDENCE`, `SEPARATE_PARSER_REQUIRED`

- Preset 是 flat INI，filename stem 承担可见名称角色；不是 JSON。
- 没有 PrusaSlicer 项目 3MF。
- 八参数在 Preset 侧需要映射，尤其是 `extrusion_multiplier`、`temperature`、`first_layer_temperature`、`min_fan_speed`、`max_fan_speed`、`fan_below_layer_time` 和 `slowdown_below_layer_time`；相似名称不等于已经证明语义等价。

## 4. 目前不可复用或必须谨慎复用的部分

可以直接复用：

- `Artifact`、`SafeZipReader` 和安全限制；
- report 的 `comparisons`、`comparison_rows`、fingerprint、source provenance 形状；
- 数值 normalization 的基础机制，但必须由 slicer adapter 先确认单位和语义；
- Preview 的非阻塞原则和现有单字段报告写入。

不能直接复用：

- `parse_bambu_3mf()` 对所有 slicer 的路径和字段假设；
- `validate_bambu_consistency()` 中的 Bambu Preset normalize；
- `_slot_match()` 的 Bambu identity 规则；
- Bambu 的 `runtime_effective_status` 及其 inheritance/runtime 解释。

## 5. 开放问题与最小补证实验

每个剩余 slicer 至少需要一组同源样本：

1. 用明确版本导出 Save Project/Save Project As 3MF；
2. 用同一项目中的 filament preset 导出对应 Preset；
3. 建立单 filament 和双 filament 两个项目；
4. 有意修改八参数中的至少一个，验证 3MF 是否反映修改；
5. 验证 slot id、filament preset name/id、plate/object assignment；
6. 分别记录未切片项目、Export 3MF 和 gcode.3mf，不混为一种格式；
7. 记录完整 ZIP member list 和配置文件摘要，不上传或打印 G-code 内容。

缺少这些样本前，所有其他 slicer 的 3MF 结论均应保持 `NOT_TESTED`/`INSUFFICIENT_EVIDENCE`。

## 6. P9-C 约束核对

本次仅进行了只读审计、ZIP 结构检查、现有 validator 的隔离实验和文档写入；没有修改 Preview、Feishu、Miaoda、publication 或生产 slicer dispatch，也没有新增生产 validator。
