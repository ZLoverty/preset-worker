"""Production processor composition.

Keeping this outside workflow services makes adding a processor a composition
change rather than a change to enrichment business logic.
"""

from .bambu_studio import BambuStudioProcessor
from .contracts import SlicerProcessorRegistry
from .creality_print import CrealityPrintProcessor
from .elegoo_slicer import ElegooSlicerProcessor
from .orca_slicer import OrcaSlicerProcessor
from .prusa_slicer import PrusaSlicerProcessor
from .snapmaker_orca import SnapmakerOrcaSlicerProcessor


# Feishu may retain the application's display label while the worker uses a
# stable business identity internally. Keep this exact alias explicit; do not
# infer slicer identity from artifact contents or fuzzy text matching.
SLICER_ID_ALIASES = {
    "OrcaSlicer (Snapmaker)": "SnapmakerOrcaSlicer",
}


def canonical_slicer_id(value: str) -> str:
    return SLICER_ID_ALIASES.get(value, value)


def default_processor_registry() -> SlicerProcessorRegistry:
    return SlicerProcessorRegistry([
        BambuStudioProcessor(),
        OrcaSlicerProcessor(),
        CrealityPrintProcessor(),
        ElegooSlicerProcessor(),
        PrusaSlicerProcessor(),
        SnapmakerOrcaSlicerProcessor(),
    ])
