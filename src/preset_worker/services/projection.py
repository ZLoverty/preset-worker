"""Current Preset projection for published process-photo attachments."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ..adapters.feishu.attachments import FeishuAttachmentAdapter


@dataclass(frozen=True)
class AttachmentProjection:
    source_field: str
    target_field: str


# These are the attachment fields that currently exist in both configured
# Submission and Preset tables.  Keep this list explicit: canonical/uploaded
# JSON attachments are historical payloads, not current process photos.
PHOTO_PROJECTIONS = (
    AttachmentProjection("冷却参数照片", "冷却参数照片"),
    AttachmentProjection("温度塔照片", "温度塔照片"),
    AttachmentProjection("最大体积流量照片", "最大体积流量照片"),
    AttachmentProjection("流量比例照片", "流量比例照片"),
    AttachmentProjection("PA校准照片", "PA校准照片"),
    AttachmentProjection("小船45°模型", "小船45°模型"),
    AttachmentProjection("综合模型45°", "综合模型45°"),
    AttachmentProjection("面包机照片", "面包机照片"),
    AttachmentProjection("回抽测试", "回抽测试"),
    AttachmentProjection("其他照片", "其他照片"),
)

# The measured 3MF is also part of the current Preset state.  It is kept on
# Submission as the historical source and is deliberately not duplicated in
# PresetVersion.
PRESET_3MF_PROJECTION = AttachmentProjection("preset 3mf", "preset 3mf")
CURRENT_ATTACHMENT_PROJECTIONS = PHOTO_PROJECTIONS + (PRESET_3MF_PROJECTION,)

logger = logging.getLogger(__name__)


class ProjectionService:
    """Materialize the current Submission photo state onto a Preset."""

    def __init__(
        self,
        client: Any,
        *,
        projections: tuple[AttachmentProjection, ...] = CURRENT_ATTACHMENT_PROJECTIONS,
        attachment_adapter: FeishuAttachmentAdapter | None = None,
    ) -> None:
        self.client = client
        self.projections = projections
        self.attachment_adapter = attachment_adapter or FeishuAttachmentAdapter()

    def project_submission_to_preset(
        self,
        *,
        submission: dict[str, Any],
        preset: dict[str, Any],
    ) -> None:
        """Replace every configured target with the source's current value.

        Missing or empty source fields become ``[]`` so old photos are
        cleared rather than retained.  All mappings are sent together, which
        makes a retry naturally idempotent and avoids attachment accumulation.
        """

        source_fields = submission.get("fields", {})
        updates = {
            projection.target_field: self.attachment_adapter.for_field(
                source_fields.get(projection.source_field)
            )
            for projection in self.projections
        }
        if updates:
            counts = {
                field: len(value)
                for field, value in updates.items()
            }
            try:
                self.client.update_record(
                    self.client.preset_table_id,
                    preset["record_id"],
                    updates,
                )
            except Exception:
                logger.exception(
                    "current projection failed submission=%s preset=%s fields=%s",
                    submission.get("fields", {}).get("submission_id", submission.get("record_id")),
                    preset.get("record_id"),
                    counts,
                )
                raise
            logger.info(
                "current projection succeeded submission=%s preset=%s fields=%s",
                submission.get("fields", {}).get("submission_id", submission.get("record_id")),
                preset.get("record_id"),
                counts,
            )
