# P9-B3-A 实现报告

## 已完成

- 在 `CandidateResult` 保留 Preview 已下载的 native Preset `source_artifact`。
- 新增 `services/consistency_preview.py`，作为 Preview 的一致性旁路适配层。
- 仅对 `BambuStudio` 执行 P9-B2 validator；其他 slicer 写入空文本。
- 缺少 `preset 3mf` 时写入空文本，不下载、不报错。
- 使用 `validate_bambu_consistency()`，不复制比较逻辑，保留完整 `comparison_rows`。
- 完整报告以 JSON 文本写入唯一字段 `consistency_report`，不上传报告附件。
- JSON 包含 `status`、UTC `generated_at` 和完整 P9-B2 `report`；每次 Preview 显式覆盖，避免旧报告残留。
- 校验器、3MF 下载和 JSON 序列化异常均被隔离；native Preview 仍按原逻辑写入 `DRAFT`。
- 报告超过 100,000 UTF-8 字节时不截断，改写为小型错误 JSON。
- 一致性字段与原有 Preview 结果合并为一次 `update_submission`，避免额外的状态写请求。

## 测试

新增 `tests/test_p9_b3_a.py`，覆盖：

- 非 Bambu 和缺少 3MF 写入空文本；
- JSON 文本及 `p9b2.consistency.v1` 保留；
- validator 异常转换为最小 `ERROR` JSON；
- 超大报告使用错误回退，且不上传附件。

验证结果：

```text
tests/test_submission_enrichment.py tests/test_p9_b3_a.py
28 passed
```

P9-B2 的 20 个聚焦测试也保持通过。部署前只需在 Feishu Submission 表增加 `consistency_report` 多行文本字段；本实现不修改 Miaoda、不改变审批或发布条件。
