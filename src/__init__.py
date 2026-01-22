"""DCS Interconnection Diagram Generator.

An AI-powered tool that automatically generates professional DCS interconnection
diagrams in PDF format from Excel I/O lists.
"""

__version__ = "1.0.0"
__author__ = "Nayyer"

from .models import (
    Instrument,
    SignalType,
    Cable,
    CableType,
    BranchCable,
    MultipairCable,
    TerminalAllocation,
    TerminalBlock,
    JunctionBox,
    MarshallingCabinet,
    DrawingMetadata,
    DrawingSheet,
    InterconnectionDrawing,
)

from .parsers import (
    IOListParser,
    load_io_list,
    filter_instruments_by_area,
    filter_instruments_by_type,
    group_instruments_by_area,
)

from .engine import (
    classify_instrument,
    classify_jb_type,
    JBType,
    size_cables_for_jb,
    allocate_all_terminals,
    TagGenerator,
)

from .drawing import (
    PDFRenderer,
    render_interconnection_diagram,
    PageLayout,
)

__all__ = [
    # Version
    "__version__",
    "__author__",
    # Models
    "Instrument",
    "SignalType",
    "Cable",
    "CableType",
    "BranchCable",
    "MultipairCable",
    "TerminalAllocation",
    "TerminalBlock",
    "JunctionBox",
    "MarshallingCabinet",
    "DrawingMetadata",
    "DrawingSheet",
    "InterconnectionDrawing",
    # Parsers
    "IOListParser",
    "load_io_list",
    "filter_instruments_by_area",
    "filter_instruments_by_type",
    "group_instruments_by_area",
    # Engine
    "classify_instrument",
    "classify_jb_type",
    "JBType",
    "size_cables_for_jb",
    "allocate_all_terminals",
    "TagGenerator",
    # Drawing
    "PDFRenderer",
    "render_interconnection_diagram",
    "PageLayout",
]
