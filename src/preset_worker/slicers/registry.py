"""Production processor composition.

Keeping this outside workflow services makes adding a processor a composition
change rather than a change to enrichment business logic.
"""

from .bambu_studio import BambuStudioProcessor
from .contracts import SlicerProcessorRegistry


def default_processor_registry() -> SlicerProcessorRegistry:
    return SlicerProcessorRegistry([BambuStudioProcessor()])
