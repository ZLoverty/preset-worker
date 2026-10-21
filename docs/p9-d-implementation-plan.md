# P9-D 多切片器一致性实现计划

## P9-D0 更新

实际 3MF 夹具已经改变了此前的优先级判断：Orca、Snapmaker Orca、CrealityPrint 和 ElegooSlicer 的项目都使用可被现有 Bambu ZIP/JSON 抽取器读取的 `Metadata/project_settings.config`；PrusaSlicer 使用独立的 `Metadata/Slic3r_PE.config`。因此 P9-D1 应先提取共享的“Bambu 风格项目 JSON”适配层，但仍保留 slicer-specific identity 和 Preset mapping。

当前验证状态：

- CrealityPrint、ElegooSlicer：真实单 filament pair，slot identity `UNIQUE`，建议进入 adapter 级实现验证；
- OrcaSlicer：真实项目和 Preset 存在，`filament_settings_id` 精确命中 slot 1/4；按约定任取其一，建议实现为最低 slot 优先的确定性选择；
- SnapmakerOrcaSlicer：真实 pair 已存在，slot 1 identity `UNIQUE`，但需要先修正“选 slot 后再比较数组”的语义；
- PrusaSlicer：真实 pair 存在；本 fixture 中用 Preset filename stem `pla_test` 精确命中项目 slot 1 且仅命中一次，因此 identity 可确定，但仍保持独立 parser 方向。

## 总体策略

保留 P9-B2 的比较结果形状和 P9-B3-A 的非阻塞 Preview 集成，只扩展“项目配置抽取”和“Preset 字段映射”边界。不要把 `bambu_parser.py` 改造成通用 3MF 大框架，也不要让 unsupported slicer 直接进入 Bambu validator。

建议的最小概念边界是：

```text
SlicerConsistencyAdapter
  -> extract_project_config(3mf bytes)
  -> identify_filament_slots()
  -> map_parameters()
  -> shared element-wise comparison/report
```

其中 adapter 负责格式、路径、identity 和单位映射；共享层负责逐元素比较、状态、provenance、fingerprint 和 `comparison_rows`。在真正证明共享结构以前，不新增 generic plugin framework。

## 推荐实现顺序

### D1 — 共享项目 JSON 抽取 + CrealityPrint/ElegooSlicer adapter 验证

这两个真实 pair 已证明项目侧八个 canonical key 都存在，且单 slot identity 分别为 `pla_test`/`pla_test`，是最小风险的 adapter 起点。实现时仍不能把报告 source 标为 BambuStudio，也不能把缺少的 Preset 参数当作零值。

验收：完整八参数 evidence、slicer-specific source/version、single-slot identity、mismatch 和 missing-Preset 参数测试。

### D2 — OrcaSlicer：先修正配对，再 `REUSE_WITH_ADAPTER`

原因：本地 Orca 源码和当前真实项目已经显示 BBL 3MF 路径、`filament_settings_id` 多值和 sequence 处理，理论复用距离最近；同一 identity 命中多个槽位时按约定选择任一匹配槽，代码中采用最低 slot 的确定性规则，并补充导出模式证据。

所需夹具：

- OrcaSlicer 版本和 printer model；
- Save Project/Save Project As 3MF；
- Export 3MF；
- sliced/gcode.3mf（如产品实际会上传）；
- 单 filament、双 filament；
- 对应 Orca Preset JSON。

验收：确认 `project_settings.config` 是否存在、八参数路径和值是否稳定、slot identity 是否能与 Preset 精确匹配。若成立，只复用 SafeZip、Bambu 风格 JSON 抽取和共享比较层，保留独立 `OrcaSlicer` adapter。

### D3 — SnapmakerOrcaSlicer：独立于标准 Orca 验证

原因：Preset 结构近似 Orca，但 fork 的继承和 printer identity 已有差异。当前真实 pair 已证明 slot 1 identity 为 `pla_test`；现有 P9-B2 probe 仍因四元素项目数组与一元素 Preset 数组直接比较而产生 `AMBIGUOUS`，需要先把 slot selection 放到比较之前。

验收：至少确认 Snapmaker 导出路径、slot identity、Snapmaker printer compatibility 和多 filament assignment。只有所有差异都被 adapter 明确处理后，才允许复用 Orca project extractor。

### D4 — PrusaSlicer：最后处理

原因：Preset 是 INI，filename stem 参与 identity；八参数至少需要一层字段映射，且 inheritance/compatible printer 在已有 round-trip 中会被清除。当前已经确认 `Slic3r_PE.config` 和四组 profile 值；外部 `pla_test.ini` 可通过 filename stem `pla_test` 唯一对应到 slot 1。仍需在更多导出样本中验证 filename stem 规则，并证明参数映射的单位和语义。

验收：必须同时验证 INI Preset 与项目中的 filament identity，并证明 `temperature`/`first_layer_temperature`、`extrusion_multiplier` 等映射的单位和语义；没有证据时只能输出 `UNRESOLVED`。

## 建议的代码改动

1. 保持 `Artifact`、`SlicerProcessor`、Preview 状态流转和 Feishu `consistency_report` 不变。
2. 将 `parse_bambu_3mf()` 中通用安全 ZIP 读取与 Bambu-specific extraction 分开，但只在第一种新 slicer 已证明需要时做小范围抽取。
3. 为每个已验证 slicer 增加独立 adapter，而不是在 `consistency.py` 增加 `if slicer == ...` 分支。
4. 把共享比较器的输入限制为已解析的 canonical preset values、project values、slot selection 和 provenance；保留当前 element-wise array semantics。
5. 报告 `source.slicer`、配置入口、slot evidence、normalization evidence 必须明确标注 slicer，不得伪装成 Bambu runtime semantics。
6. Preview 只在 adapter 宣布 `SUPPORTED` 且有完整输入时调用；缺失 fixture/配置返回空或 informational unresolved，不改变 native Preview。

## 测试和夹具要求

每个 slicer 至少需要：

- 一个真实 single-filament 配对 fixture；
- 一个真实 multi-filament 配对 fixture；
- 一个有意 mismatch fixture；
- 一个缺少目标参数或 nil/ambiguous 数组 fixture；
- ZIP member inventory 和不包含敏感 G-code 内容的摘要；
- Preset、3MF、slicer version、printer model、导出模式的 manifest。

测试必须分别覆盖：slot 选择、0/1-based 转换、identity mismatch、array length mismatch、单位 normalization、inheritance unresolved、plate/object assignment 和完整 `comparison_rows`。

## 接受标准

某一 slicer 只有同时满足以下条件，才可从 `NOT_TESTED` 进入生产一致性检查：

1. 有真实 Preset + 3MF 配对证据；
2. ZIP 配置路径和格式已固定；
3. 至少八参数的每项都有 `DIRECT`、`MAPPED` 或明确 `CONDITIONAL` 结论；
4. filament identity 和 slot selection 可复现；
5. mismatch、ambiguous、missing 和多 slot 都有测试；
6. report provenance 能区分 stored equality 与 runtime-effective status；
7. adapter 失败不会阻断 native Preview；
8. 不修改 approval/publication 条件。

## 明确延期

- 未取得真实 fixture 前的其他 slicer 生产接入；
- 自动从 G-code 反推 filament 参数；
- 全量 inheritance resolution；
- 把所有 3MF 统一成一个通用插件框架；
- 历史报告回填；
- Miaoda UI 改动；
- 任何未经 fixture 证明的参数别名或单位转换。
