# P9-C Slicer Compatibility Matrix

## 分类说明

- `DIRECT`：两侧字段和语义已由真实配对证据确认。
- `MAPPED`：字段名或格式不同，但已有足够证据证明可作确定映射。
- `CONDITIONAL`：只有在特定项目导出模式、slot 或 runtime 条件满足时才可比较。
- `UNRESOLVED`：存在候选字段或推测，但缺少真实配对 3MF/语义证据。
- `UNSUPPORTED`：已证明不可用；本次没有把“缺少证据”误标为此类。

## Slicer-level overview

| Slicer | Preset 证据 | 3MF 配对证据 | 3MF 结构结论 | 复用潜力 | 当前状态 |
|---|---|---|---|---|---|
| BambuStudio | JSON，已覆盖当前 Bambu processor | `PPS100CF10 H2D` 配对 | `project_settings.config` JSON + Bambu metadata | `REUSE_AS_IS`（当前 Bambu 范围） | `VERIFIED_FOR_CURRENT_FIXTURE` |
| OrcaSlicer | JSON；目标字段分散在已有 fixture | 无 | Orca 源码显示 BBL 3MF 路径，但未实测导出物 | `REUSE_WITH_ADAPTER` 候选 | `NOT_TESTED` |
| SnapmakerOrcaSlicer | JSON；独立 fork identity | 无 | 未知 | `INSUFFICIENT_EVIDENCE` | `NOT_TESTED` |
| CrealityPrint | JSON；已有 round-trip 证据 | 无 | 未知 | `SEPARATE_PARSER_REQUIRED` 候选 | `NOT_TESTED` |
| ElegooSlicer | JSON；已有 round-trip 证据 | 无 | 未知 | `SEPARATE_PARSER_REQUIRED` 候选 | `NOT_TESTED` |
| PrusaSlicer | INI；filename 参与 identity | 无 | 未知；不能沿用 JSON 假设 | `SEPARATE_PARSER_REQUIRED` | `NOT_TESTED` |

“复用潜力”是实现建议，不是兼容性证明。除 Bambu 当前 fixture 外，没有其他 slicer 达到 `VERIFIED`。

## Eight-parameter matrix

下表中的“Preset-side candidate”只表示现有 Preset fixture 中观察到的字段；“3MF-side evidence”没有真实配对项目时统一标为 `UNRESOLVED`。这避免把 Preset 文件可解析误当成项目 3MF 可比较。

| 参数 | BambuStudio | OrcaSlicer | SnapmakerOrcaSlicer | CrealityPrint | ElegooSlicer | PrusaSlicer |
|---|---|---|---|---|---|---|
| `filament_flow_ratio` | `DIRECT`；3MF `project_settings.config`；数组按 slot | `UNRESOLVED`；Preset `filament_flow_ratio` 已见，3MF 未测 | `UNRESOLVED`；Preset 未见，3MF 未测 | `UNRESOLVED`；Preset 未见，3MF 未测 | `UNRESOLVED`；Preset 未见，3MF 未测 | `UNRESOLVED`；候选 `extrusion_multiplier`，3MF 未测 |
| `filament_max_volumetric_speed` | `DIRECT`；同名 JSON 数组 | `UNRESOLVED`；Preset 同名，3MF 未测 | `UNRESOLVED`；Preset 未见，3MF 未测 | `UNRESOLVED`；Preset 未见，3MF 未测 | `UNRESOLVED`；Preset 未见，3MF 未测 | `UNRESOLVED`；Preset 同名，3MF 未测 |
| `nozzle_temperature` | `DIRECT`；同名 JSON 数组 | `UNRESOLVED`；Preset `nozzle_temperature`，3MF 未测 | `UNRESOLVED`；Preset 同名，3MF 未测 | `UNRESOLVED`；Preset 同名，3MF 未测 | `UNRESOLVED`；Preset 同名，3MF 未测 | `UNRESOLVED`；候选 `temperature`，3MF 未测 |
| `nozzle_temperature_initial_layer` | `DIRECT`；同名 JSON 数组 | `UNRESOLVED`；Preset 同名，3MF 未测 | `UNRESOLVED`；Preset 同名，3MF 未测 | `UNRESOLVED`；Preset 同名，3MF 未测 | `UNRESOLVED`；Preset 同名，3MF 未测 | `UNRESOLVED`；候选 `first_layer_temperature`，3MF 未测 |
| `fan_min_speed` | `DIRECT`；同名 JSON 数组 | `UNRESOLVED`；Preset 未见，3MF 未测 | `UNRESOLVED`；Preset 未见，3MF 未测 | `UNRESOLVED`；Preset 未见，3MF 未测 | `UNRESOLVED`；Preset `fan_min_speed`，3MF 未测 | `UNRESOLVED`；候选 `min_fan_speed`，3MF 未测 |
| `fan_max_speed` | `DIRECT`；同名 JSON 数组 | `UNRESOLVED`；Preset 未见，3MF 未测 | `UNRESOLVED`；Preset 未见，3MF 未测 | `UNRESOLVED`；Preset 未见，3MF 未测 | `UNRESOLVED`；Preset 未见，3MF 未测 | `UNRESOLVED`；候选 `max_fan_speed`，3MF 未测 |
| `fan_cooling_layer_time` | `DIRECT`；同名 JSON 数组 | `UNRESOLVED`；Preset 同名，3MF 未测 | `UNRESOLVED`；Preset 同名，3MF 未测 | `UNRESOLVED`；Preset 同名，3MF 未测 | `UNRESOLVED`；Preset 同名，3MF 未测 | `UNRESOLVED`；候选 `fan_below_layer_time`，3MF 未测 |
| `slow_down_layer_time` | `DIRECT`；同名 JSON 数组 | `UNRESOLVED`；Preset 未见，3MF 未测 | `UNRESOLVED`；Preset 未见，3MF 未测 | `UNRESOLVED`；Preset 未见，3MF 未测 | `UNRESOLVED`；Preset 未见，3MF 未测 | `UNRESOLVED`；候选 `slowdown_below_layer_time`，3MF 未测 |

## Identity and slot matrix

| Slicer | Preset identity candidate | Project slot evidence | Index convention | 风险 |
|---|---|---|---|---|
| BambuStudio | `filament_settings_id` | 真实 fixture 中与 project slot 精确匹配 | Worker 内部 slot id 1-based；数组下标 0-based | 多 slot、nil 和 inheritance 仍需保持 unresolved |
| OrcaSlicer | `filament_settings_id`/name | Orca 源码存在多值 `filament_settings_id`，但无真实项目样本 | 源码显示 sequence 文件 1-based，读取转 0-based | Save Project 与 gcode.3mf 可能不是同一语义 |
| SnapmakerOrcaSlicer | `filament_settings_id`/name | 未测试 | 未知 | fork 的 printer/material identity 未建立 |
| CrealityPrint | `filament_settings_id`/name/base_id 候选 | 未测试 | 未知 | `base_id` 已证明会归一化，不能当作 slot identity |
| ElegooSlicer | `filament_settings_id`/name | 未测试 | 未知 | 无 UUID、printer id 或项目 slot 证据 |
| PrusaSlicer | filename stem；`filament_settings_id` 当前为空候选 | 未测试 | 未知 | INI 没有显式 name；外部 profile round-trip 受限 |

## Provenance and runtime semantics

当前报告中的 `selection.status` 和 `runtime_effective_status` 可以保留，但其他 slicer 必须由各自 adapter 填充证据。不能把存储值相同直接提升为 runtime-effective 等价；尤其是继承配置、项目覆盖、plate/object assignment 和多挤出机映射未建立时，应该输出 `UNRESOLVED` 或 `AMBIGUOUS`。
