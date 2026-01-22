"""Terminal data models for DCS interconnection diagrams."""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class TerminalStatus(Enum):
    """Terminal allocation status."""
    USED = "USED"
    SPARE = "SPARE"
    RESERVED = "RESERVED"


class EquipmentLocation(Enum):
    """Equipment location type."""
    JUNCTION_BOX = "JB"
    MARSHALLING_CABINET = "CABINET"


@dataclass
class TerminalAllocation:
    """Represents a single terminal allocation."""

    terminal_number: int          # Terminal sequence number
    terminal_positive: str        # Positive terminal label (e.g., "1+")
    terminal_negative: str        # Negative terminal label (e.g., "1-")
    terminal_shield: Optional[str] = None  # Shield terminal label (e.g., "1S")
    terminal_pair: Optional[str] = None    # Pair label for cabinet (e.g., "PR1")
    wire_color_positive: str = "WH"        # Wire color for positive
    wire_color_negative: str = "BK"        # Wire color for negative
    instrument_tag: Optional[str] = None   # Associated instrument
    dcs_tag: Optional[str] = None          # DCS point tag
    status: TerminalStatus = TerminalStatus.SPARE

    @property
    def is_used(self) -> bool:
        return self.status == TerminalStatus.USED

    @property
    def is_spare(self) -> bool:
        return self.status == TerminalStatus.SPARE


@dataclass
class TerminalBlock:
    """Represents a terminal block in JB or Cabinet."""

    tag_number: str              # e.g., "TB601-I0004"
    location: EquipmentLocation  # JB or CABINET
    parent_equipment: str        # JB or Cabinet tag
    total_terminals: int         # Total available terminals
    allocations: List[TerminalAllocation] = field(default_factory=list)

    @property
    def used_terminals(self) -> int:
        """Count of used terminals."""
        return sum(1 for a in self.allocations if a.is_used)

    @property
    def spare_terminals(self) -> int:
        """Count of spare terminals."""
        return sum(1 for a in self.allocations if a.is_spare)

    @property
    def utilization_percent(self) -> float:
        """Calculate terminal utilization percentage."""
        if self.total_terminals == 0:
            return 0.0
        return (self.used_terminals / self.total_terminals) * 100

    @property
    def spare_percent(self) -> float:
        """Calculate spare percentage."""
        if self.total_terminals == 0:
            return 0.0
        return (self.spare_terminals / self.total_terminals) * 100

    def get_allocation(self, instrument_tag: str) -> Optional[TerminalAllocation]:
        """Get terminal allocation for a specific instrument."""
        for allocation in self.allocations:
            if allocation.instrument_tag == instrument_tag:
                return allocation
        return None

    def get_spare_allocations(self) -> List[TerminalAllocation]:
        """Get all spare terminal allocations."""
        return [a for a in self.allocations if a.is_spare]

    def get_used_allocations(self) -> List[TerminalAllocation]:
        """Get all used terminal allocations."""
        return [a for a in self.allocations if a.is_used]


@dataclass
class JunctionBox:
    """Represents a Junction Box."""

    tag_number: str              # e.g., "PP01-601-IAJB0002"
    jb_type: str                 # "ANALOG" or "DIGITAL"
    area: str                    # Plant area
    terminal_block: Optional[TerminalBlock] = None
    multipair_cable_tag: Optional[str] = None

    @property
    def is_analog(self) -> bool:
        return self.jb_type == "ANALOG"

    @property
    def is_digital(self) -> bool:
        return self.jb_type == "DIGITAL"

    @property
    def instrument_count(self) -> int:
        """Count of instruments connected to this JB."""
        if self.terminal_block:
            return self.terminal_block.used_terminals
        return 0


@dataclass
class MarshallingCabinet:
    """Represents a Marshalling Cabinet."""

    tag_number: str              # e.g., "PP01-601-ICP001"
    area: str                    # Plant area
    terminal_blocks: List[TerminalBlock] = field(default_factory=list)

    def add_terminal_block(self, tb: TerminalBlock):
        """Add a terminal block to the cabinet."""
        self.terminal_blocks.append(tb)

    def get_terminal_block(self, tag: str) -> Optional[TerminalBlock]:
        """Get terminal block by tag."""
        for tb in self.terminal_blocks:
            if tb.tag_number == tag:
                return tb
        return None

    @property
    def total_terminals(self) -> int:
        """Total terminals across all terminal blocks."""
        return sum(tb.total_terminals for tb in self.terminal_blocks)

    @property
    def used_terminals(self) -> int:
        """Total used terminals across all terminal blocks."""
        return sum(tb.used_terminals for tb in self.terminal_blocks)
