"""Data models for DCS interconnection diagram generator."""

from .instrument import (
    Instrument,
    SignalType,
    INSTRUMENT_CLASSIFICATION,
)

from .cable import (
    Cable,
    CableType,
    BranchCable,
    MultipairCable,
    MULTIPAIR_SIZES,
    CABLE_SPECIFICATIONS,
    MULTIPAIR_SPECS,
    get_multipair_spec,
)

from .terminal import (
    TerminalAllocation,
    TerminalBlock,
    TerminalStatus,
    EquipmentLocation,
    JunctionBox,
    MarshallingCabinet,
)

from .drawing import (
    DrawingMetadata,
    DrawingSheet,
    InterconnectionDrawing,
    DrawingProject,
)

from .io_card import (
    IOModule,
    IOCard,
    Controller,
    IOAllocationResult,
    ControlSystem,
    IOType,
    SILRating,
)

__all__ = [
    # Instrument
    "Instrument",
    "SignalType",
    "INSTRUMENT_CLASSIFICATION",
    # Cable
    "Cable",
    "CableType",
    "BranchCable",
    "MultipairCable",
    "MULTIPAIR_SIZES",
    "CABLE_SPECIFICATIONS",
    "MULTIPAIR_SPECS",
    "get_multipair_spec",
    # Terminal
    "TerminalAllocation",
    "TerminalBlock",
    "TerminalStatus",
    "EquipmentLocation",
    "JunctionBox",
    "MarshallingCabinet",
    # Drawing
    "DrawingMetadata",
    "DrawingSheet",
    "InterconnectionDrawing",
    "DrawingProject",
    # I/O Card Allocation
    "IOModule",
    "IOCard",
    "Controller",
    "IOAllocationResult",
    "ControlSystem",
    "IOType",
    "SILRating",
]
