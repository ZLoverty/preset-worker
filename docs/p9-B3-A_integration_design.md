# P9-B3-A Worker Preview 集成设计

## 实际调用链

`WorkerRuntime.run_once()` 通过 `list_preview_candidates()` 找到 `status=PREVIEW_REQUESTED` 的 Submission，随后调用：

```text
WorkerRuntime._dispatch
  -> PreviewService.preview_submission(record=discovered_record)
     -> SubmissionEnrichment.process_candidate
        -> 下载 preset data / uploaded_json
        -> slicer processor parse / validate / normalize / policy / serialize
        -> 生成 UnifiedDiff
     -> 上传或复用 canonical_json
     -> 生成一致性字段（可选旁路）
     -> 单次 update_submission，写入 Preview 结果并回到 DRAFT
```

原生 Preview 的 Preset JSON 是 `process_candidate()` 中下载的第一个 `preset data` 附件。3MF 位于 Submission 的 `preset 3mf` 附件字段，当前 Preview 之前没有读取它。`FeishuClient` 已提供统一的 `download_attachment()` 和 `upload_attachment()`，因此不增加新的 Feishu metadata 查询层。

## 最小集成点

在 `CandidateResult` 保留已经下载的 `source_artifact`，避免再次下载 native Preset。原生候选生成和 canonical/diff 流程保持不变；Preview 成功后，由 `consistency_preview.build_consistency_report()`：

1. 仅对 slicer 精确等于 `BambuStudio` 的记录继续处理。
2. 没有 `preset 3mf` 时返回空文本。
3. 下载 3MF 并调用唯一的 `validate_bambu_consistency()`。
4. 将完整 `p9b2.consistency.v1` 报告封装并序列化为多行文本 JSON。
5. 把 JSON 文本合并到原有 Preview 的同一个 `update_submission` 请求。

不支持的 slicer 和缺少 3MF 都写入空字符串。校验器异常写入最小 `ERROR` JSON。所有一致性异常都在该边界被捕获，不会改变 native Preview 的返回值或 `DRAFT` 状态。

## Feishu 字段

只使用一个字段：

| 字段 | 写入内容 |
|---|---|
| `consistency_report` | 多行文本 JSON；无报告时为空字符串 |

JSON 顶层包含 `status`、UTC `generated_at` 和完整的 `report`；执行错误使用最小 `error` 对象。每次 Preview 都显式覆盖该字段，因此旧报告会被清空或替换；本阶段不做历史回填，也不新增 Submission 生命周期状态。

## 并发、重试与失败边界

Worker 当前按轮次串行 dispatch，且 Preview 入口仍要求 `PREVIEW_REQUESTED`。原有状态写入保持单次 PUT；一致性生成失败时，仍写入最小 `ERROR` JSON，不会阻断 canonical JSON 或 Preview 状态写入。报告按 UTF-8 字节数限制为 100,000 字节，超限不截断而改写为错误 JSON。重复请求只可能在记录仍为 `PREVIEW_REQUESTED` 时发生，最终报告以最后一次成功 Preview 的文本为准。

## 已知部署前提

部署前需要在 Submission 表创建 `consistency_report` 多行文本字段。Miaoda 前端不在本阶段修改；后续可直接解析文本 JSON 中的 `report.comparison_rows` 做逐项表格展示。
