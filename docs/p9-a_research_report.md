# P9-A 调研报告：Bambu Studio 3MF 项目设置与 Preset 一致性可行性

调研日期：2026-10-20。范围：Bambu Studio；研究、逆向与可行性验证，不包含生产接入。

## 结论摘要

可以对一部分参数进行可靠的条件比较，但不能把任意 3MF 与单个 Filament Preset JSON 做无条件的全量一致性校验。

关键原因：

1. Metadata/project_settings.config 是项目配置快照；缺失、nil、默认值和继承关系不能仅凭字段出现与否推断。
2. 参数数组不等于 filament 数组；项目中同时存在 filament、extruder/nozzle、process 和 plate 维度。
3. Metadata/model_settings.config 能给出 object/volume 到 filament slot 的映射；plate 级 filament map 在 model config 的 plater 元数据中表达。
4. Metadata/filament_sequence.json 记录切换/分配序列，不是 filament preset 参数来源。
5. 压力提前（PA）在 Bambu 打印机上源码明确标注为无效/不写入 BBL G-code；不能因为 3MF 中有数值就判定 PA 已生效。
6. 当前 BambuStudioProcessor 只解析和原样复制 JSON，再施加 name 与 pm_method_version；没有 3MF 解析、继承解析或参数语义归一化。

建议 P9-B 只比较“可获得且上下文明确”的参数，输出逐参数结果和证据，不输出单一 PASS/FAIL。

## 1. 仓库审计

现有可复用接口：

- src/preset_worker/slicers/bambu_studio.py：BambuStudioProcessor。parse 做 UTF-8 JSON 解析；validate_source 要求顶层 object、非空字符串 key 和 version；normalize 只是 deepcopy；apply_company_policy 只覆盖 name 和 pm_method_version；diff 按递归路径和数组索引比较，没有数值容差、单位转换或 inheritance resolution。
- src/preset_worker/slicers/contracts.py：Artifact 是不透明 bytes；现有 processor contract 不包含第二个 3MF artifact，也没有一致性报告型返回值。
- src/preset_worker/services/projection.py：已有 preset 3mf 附件投影，可复用附件定位，但不能复用为解析器。
- src/preset_worker/diff.py：UnifiedDiff 适合 preset artifact diff，不足以表达 UNRESOLVED、AMBIGUOUS、NOT_COMPARABLE。
- 现有测试没有 Bambu 3MF fixture、ZIP 安全测试或跨 artifact consistency 测试。

现有 Bambu canonicalization 不解析继承、不把 nil 补成默认值、不重排数组、不改变参数值。因此比较时应使用 processor 产出的 canonical JSON，并记录 canonicalization 版本和 fingerprint；不能假定 canonical JSON 已经是 effective preset。

## 2. 实际 3MF fixture

唯一发现的真实 fixture：

downloads/legacy_preset_data_audit/recvgKBtHJUrDm_1_PPS100CF10 H2D.3mf

unzip -l 观察：

| 项目 | 观察 |
|---|---|
| ZIP entry 数量 | 105 |
| 未压缩大小 | 38,514,163 bytes |
| plate thumbnail | plate_1 到 plate_13，另有 small/no_light/top/pick 图 |
| 项目配置 | Metadata/project_settings.config，64,535 bytes，JSON object |
| 模型配置 | Metadata/model_settings.config，66,713 bytes，XML config |
| slice 信息 | Metadata/slice_info.config，205 bytes，XML header |
| filament sequence | Metadata/filament_sequence.json，928 bytes |
| embedded preset | 未发现 filament_settings_*、machine_settings_*、process_settings_* |
| sliced G-code | 未发现 Metadata/plate_N.gcode |

关键 project_settings.config 值：

    default_filament_profile: ["Bambu PLA Basic @BBL H2D"]
    filament_settings_id: ["PPS100CF10 H2D"]
    filament_type: ["PPS-CF"]
    filament_ids: ["GFT98"]
    filament_map: ["1"]
    filament_flow_ratio: ["1", "0.96"]
    filament_max_volumetric_speed: ["8", "3"]
    nozzle_temperature: ["350", "320"]
    nozzle_temperature_initial_layer: ["350", "320"]
    fan_min_speed: ["0"]
    fan_max_speed: ["30"]
    fan_cooling_layer_time: ["20"]
    enable_pressure_advance: ["0"]
    pressure_advance: ["0.02"]
    filament_retraction_length: ["nil", "nil"]
    retraction_length: ["0.8", "0.8", "0.8", "0.8", "0.8"]
    retraction_speed: ["30", "30", "30", "30", "30"]
    printer_model: "Bambu Lab H2D"
    printer_settings_id: "Bambu Lab H2D 0.4 nozzle"
    default_print_profile: "0.20mm Standard @BBL H2D"
    layer_height: "0.2"
    curr_bed_type: "Textured PEI Plate"

filament_settings_id 只有一个值，但若干 filament 参数数组有两个值，另一些 printer/extruder 参数数组有五个值。因此不能按数组长度选择 slot，也不能把第一个元素无条件当作 effective value。

different_settings_to_system 记录项目相对系统设置的差异，包括 filament_flow_ratio、filament_max_volumetric_speed、nozzle_temperature 等。它是 override 线索，但不是完整 provenance graph。

model_settings.config 是 XML。fixture 中 object/volume metadata 出现 extruder="1"，同时包含 object-level print_flow_ratio、speed 等 overrides；object-level flow 不能直接等同于 filament-level flow。

fixture 有 13 组 plate thumbnail，但只有 Metadata/plate_2.json。该 JSON 提供 bbox、bed type、filament ids、first extruder、nozzle diameter 等 slice/preview 信息，不是所有 plate 的完整配置。

filament_sequence.json 为各 plate 写入 nozzle_sequence、optimal_assignment、sequence，本 fixture 均为空。源码确认其内部序列导出为 1-based index；它不是 preset 参数来源。

## 3. 源码确认

本地 BambuStudio checkout：commit 79df7ae30。

源码定义并读取：

- Metadata/project_settings.config
- Metadata/model_settings.config
- Metadata/slice_info.config
- Metadata/filament_sequence.json
- Metadata/filament_settings_...
- Metadata/machine_settings_...
- Metadata/process_settings_...

project_settings.config 通过 DynamicPrintConfig::load_from_json() 直接载入；embedded preset 是可选独立 entry。当前 fixture 没有 embedded preset，无法验证完整 inheritance chain。

Bambu 源码对 object 的 extruder 做边界修正：slot 为 0 或大于 filament_settings_id 数量时回退到 1；这说明 object extruder 是 1-based。

### 索引模型

get_filament_config_idx() 先由 filament_map 找 extruder，再结合 filament_volume_map、extruder type、filament variant 和 self index 计算配置索引。Extruder::filament_flow_ratio()、retraction_length() 等都通过此函数取值。

报告必须保留：

    filament_slot_id (3MF metadata 中为 1-based)
    filament_config_index
    extruder_index
    plate_id
    object_id / volume_id
    nozzle_diameter / nozzle_volume_type / extruder_variant

### plate type 与 bed temperature

源码定义 cool_plate_temp、eng_plate_temp、hot_plate_temp、textured_plate_temp、supertack_plate_temp 及 initial-layer 版本；curr_bed_type 或 plater bed_type 决定使用哪一组。生成 G-code 时还可能按最高温度策略计算目标温度。

因此 bed temperature 必须按 plate type、layer phase、resolved filament/extruder index 比较。

### pressure advance

enable_pressure_advance 和 pressure_advance 存在于 config，但 tooltip 标注对 Bambu printer 无效；G-code 逻辑只在非 Bambu printer 时写 PA command。因此 Bambu printer 上应标记 NOT_COMPARABLE 或 DISPLAY_ONLY。

## 4. 参数 mapping

| parameter_id | preset_json_path | 3MF project path | ownership | cardinality | effective value | 分类 | confidence |
|---|---|---|---|---|---|---|---|
| nozzle_temperature | 同名 | project_settings.config:nozzle_temperature | FILAMENT/PROJECT | config index | 需解析索引 | CONDITIONAL | VERIFIED |
| nozzle_temperature_initial_layer | 同名 | 同名 | FILAMENT/PROJECT | config index | 需解析索引 | CONDITIONAL | VERIFIED |
| bed_temperature | 各 plate_temp | 同名；plate type 来自 curr_bed_type/plater | FILAMENT/PLATE | plate + phase + filament | 条件可得 | CONDITIONAL | VERIFIED |
| bed_temperature_initial_layer | 各 plate_temp_initial_layer | 同名 | FILAMENT/PLATE | plate + phase + filament | 条件可得 | CONDITIONAL | VERIFIED |
| filament_flow_ratio | 同名 | 同名；object 另有 model_settings.config:print_flow_ratio | FILAMENT/PROJECT/OBJECT | config index | 条件可得 | CONDITIONAL | VERIFIED |
| filament_max_volumetric_speed | 同名 | 同名 | FILAMENT/PROJECT | config index | 需解析索引 | CONDITIONAL | VERIFIED |
| fan_min_speed / fan_max_speed | 同名 | 同名 | FILAMENT/PROJECT | config-dependent | 需确认索引 | CONDITIONAL | PARTIAL |
| fan_cooling_layer_time | 同名 | 同名 | FILAMENT/PROJECT | config-dependent | 需确认索引 | CONDITIONAL | PARTIAL |
| auxiliary_fan | 同名 | project_settings.config:auxiliary_fan | PROCESS/PRINTER/PROJECT | global | 仅存储值可得 | DISPLAY_ONLY | PARTIAL |
| enable_pressure_advance / pressure_advance | 同名 | 同名 | FILAMENT/PRINTER | config index | Bambu printer 不可得 | NOT_COMPARABLE | VERIFIED |
| filament_retraction_length / filament_retraction_speed | 同名 | 同名可能为 nil | FILAMENT | config index | 无完整 resolution 不可得 | UNSUPPORTED | PARTIAL |
| retraction_length / retraction_speed | 可能继承/派生 | 同名 | PRINTER/EXTRUDER/PROJECT | config index | 条件可得 | CONDITIONAL | VERIFIED |
| deretraction_speed | 可能继承/派生 | 同名 | PRINTER/EXTRUDER/PROJECT | config index | 条件可得 | CONDITIONAL | PARTIAL |
| filament_settings_id | 同名 | 同名 | FILAMENT/PROJECT | slot | 可作 resolver 输入 | DISPLAY_ONLY | VERIFIED |
| filament_type | 同名 | 同名 | FILAMENT | slot | 可得 | DISPLAY_ONLY | VERIFIED |
| printer_model | context | 同名 | PRINTER | global | 可得 | DISPLAY_ONLY | VERIFIED |
| nozzle_diameter | context | 同名 / plate_N.json:nozzle_diameter | PRINTER/PLATE | extruder/plate | 可得 | DISPLAY_ONLY | VERIFIED |
| process_settings_id | context | 同名或 embedded process preset | PROCESS | global | 条件可得 | DISPLAY_ONLY | PARTIAL |
| layer_height | context | project_settings.config:layer_height | PROCESS/OBJECT | global/object | 可得 | DISPLAY_ONLY | VERIFIED |
| plate_type | context | curr_bed_type / plater bed_type / plate JSON | PLATE | plate | 条件可得 | DISPLAY_ONLY | VERIFIED |

未知路径没有猜填。

## 5. 继承、覆盖与缺失语义

已确认：

- project config 是项目配置快照，不是提交 JSON 的简单引用；
- filament_settings_id 识别 slot，object extruder 连接 object/volume 与 slot；
- model metadata 可覆盖 object/process 参数；
- plater metadata 可覆盖 bed type 与 filament map；
- filament effective index 由多个 machine/filament 维度共同计算；
- Bambu printer 上 PA 数值不表示已生效。

当前无法从 fixture 证明：

- embedded preset 父链；
- save-before/save-after 单参数差异；
- sliced/unsliced 差异；
- 多 filament、多 plate override precedence；
- reopen/resave 行为。

validator 必须区分：

    MISSING_IN_PRESET
    MISSING_IN_3MF
    UNRESOLVED
    AMBIGUOUS
    NOT_COMPARABLE
    MISMATCH

缺失、未解析和歧义不能直接判为 mismatch。

## 6. 多 filament / 多 plate

slot resolver 建议顺序：

1. 用户显式选择 slot；
2. canonical filament_settings_id 精确匹配；
3. preset name / stable id 精确匹配；
4. 仅唯一候选时用 type/name 辅助匹配；
5. 多候选或无候选时返回 AMBIGUOUS / UNRESOLVED，不得选第一个。

最小报告粒度：

    plate -> object/volume -> filament slot -> effective parameter set

即使多个 plate 复用同一 slot，也必须保留每个 plate 的 provenance；plate type 或 filament map 不同时必须分别比较。

## 7. 归一化规则

- 数值字符串和 JSON number 解析为 Decimal/高精度数；原始字符串保留在 evidence。
- 温度按 °C 整数比较；非整数或超范围产生 warning。
- flow ratio 统一为无量纲 ratio，如 0.96；不按字符串比较 96% 与 0.96。
- max volumetric speed 使用 mm³/s；不与线速度混比。
- fan speed 统一到 percentage；不得与 PWM 量纲混用。
- bool 接受 Bambu 常见的 0/1，保留原始 representation。
- nil、空字符串、null、缺失分别记录；都不能直接等同默认值。
- 数组比较必须经过 parameter-specific index resolution。
- 只有在同版本 schema/source code 明确可重建时才使用默认值。
- 不使用一个全局 numeric epsilon；按参数语义定义容差。

## 8. P9-B 最小架构

保持 BambuStudioProcessor 负责提交 JSON 的解析/canonicalization；新增只读链路：

    3MF bytes
      -> SafeZipReader
      -> Bambu3MFArchiveExtractor
      -> RawProject/Model/Plate records
      -> EffectiveConfigResolver
      -> FilamentSlotResolver
      -> ParameterNormalizer
      -> ConsistencyReportBuilder

建议概念接口：

    parse_project(artifact) -> BambuProjectSnapshot
    resolve_slots(snapshot, preset_json) -> SlotResolution
    resolve_effective_values(snapshot, slot_resolution) -> EffectiveValueSet
    compare(preset_json, effective_values, context) -> ConsistencyReport

解析器必须只读、不重写上传的 3MF；以 archive entry/path 作为 provenance；允许 unresolved/ambiguous/not-comparable；以两个 artifact 的 SHA-256 作为 report input fingerprint。

建议报告 schema：p9a.consistency.v1。至少包含 schema version、slicer/version、preset/3MF fingerprint、slot selection evidence、plate/printer/process context、逐参数结果、summary counts、warnings 和 errors。每项 comparison 包含 parameter id、status、原始/归一化值、source paths、resolution provenance、normalization rule、confidence。

## 9. ZIP 安全建议

在 JSON/XML 解析前审计 central directory；不要 extractall() 到用户可控路径。

| 限制 | 建议初值 |
|---|---:|
| compressed archive size | 256 MiB |
| total uncompressed size | 1 GiB |
| entry count | 10,000 |
| single entry uncompressed size | 256 MiB |
| compression ratio | 100:1，超过则拒绝或 warning |
| path | canonical relative path；拒绝绝对路径、..、NUL |
| duplicate names | 拒绝 |
| compression method | 仅允许明确支持的 method |
| JSON/XML nesting | 设置深度上限 |

## 10. 实验缺口

当前环境没有可证明运行的 Bambu Studio GUI/CLI 实验，也没有成对 fixture。下一步应固定版本建立最小项目，分别测试：单参数 preset 修改、项目 override、继承、字段缺失、printer/process 参数、plate type、多个 slot、多个 plate、unsliced/sliced、reopen/resave，并保存每个 archive entry 的 hash/key diff、操作记录和版本号。

在这些实验完成前，继承解析、save/reopen 稳定性、slice 后 effective output、plate-specific precedence 只能标记 PARTIALLY_VERIFIED。

## 11. 最终判断

P9-B 可实现一个证据驱动、条件式的一致性检查器，首期优先覆盖：

- nozzle temperature / initial-layer nozzle temperature；
- filament flow ratio；
- max volumetric speed；
- fan min/max 与 cooling time（索引和 scope 已解析时）；
- 当前 plate type 下的 bed temperature；
- printer/process/plate context 展示。

首期不应把以下内容作为 Bambu filament preset 的硬一致性条件：

- Bambu printer 上的 pressure advance；
- project 中为 nil、实际使用 printer/extruder retraction_* 的 filament retraction；
- 无法解析 inherited parent 或多 slot 匹配的情况；
- object-level print_flow_ratio 与 filament-level filament_flow_ratio 的混合比较。

核心边界：比较已解析的 effective value，而不是比较 archive 中看起来相似的字段。

## 证据索引

- 仓库：src/preset_worker/slicers/bambu_studio.py、contracts.py、services/projection.py、diff.py。
- 真实 fixture：downloads/legacy_preset_data_audit/recvgKBtHJUrDm_1_PPS100CF10 H2D.3mf。
- BambuStudio checkout 79df7ae30：src/libslic3r/Format/bbs_3mf.cpp、PrintConfig.cpp、Extruder.cpp、GCode.cpp。
- 官方源码：https://github.com/bambulab/BambuStudio/blob/master/src/libslic3r/Format/bbs_3mf.cpp
- 官方 CLI 文档：https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage/b6cc1075234d09380eb3450f702aec8b3896eefb
