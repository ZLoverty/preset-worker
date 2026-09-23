"""Feishu attachment transfer primitives used by current projections."""

from __future__ import annotations

import copy
from typing import Any

from ...services.enrichment import _attachment_list


class FeishuAttachmentAdapter:
    """Prepare attachment field values for a Bitable update.

    Bitable accepts an existing attachment ``file_token`` in another record
    in this Base.  Keeping the adapter responsible for this detail lets the
    projection service remain about field mapping only.
    """

    def for_field(self, value: object) -> list[dict[str, Any]]:
        # Preserve the API's source order and metadata.  A deep copy also
        # prevents a projection from mutating the historical Submission.
        return copy.deepcopy(_attachment_list(value))
