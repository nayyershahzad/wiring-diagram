"""I/O Card and Controller data models for Yokogawa systems."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class ControlSystem(Enum):
    """Control system types."""
    DCS = "DCS"           # CENTUM VP
    SIS = "SIS"           # ProSafe-RS (ESD)
    RTU = "RTU"           # STARDOM/FA-M3


class IOType(Enum):
    """I/O signal types."""
    AI = "AI"    # Analog Input
    AO = "AO"    # Analog Output
    DI = "DI"    # Digital Input
    DO = "DO"    # Digital Output


class SILRating(Enum):
    """Safety Integrity Level ratings."""
    NONE = 0
    SIL1 = 1
    SIL2 = 2
    SIL3 = 3


@dataclass
class IOModule:
    """Represents an I/O module/card specification."""
    model: str                    # e.g., "AAI143-H00"
    io_type: IOType              # AI, AO, DI, DO
    channels: int                # Number of channels per card
    signal_type: str             # "4-20mA", "24VDC", etc.
    features: List[str] = field(default_factory=list)  # ["HART", "Isolated", etc.]
    sil_rating: Optional[SILRating] = None
    control_system: Optional[ControlSystem] = None
    vendor: str = "Yokogawa"

    @property
    def is_safety_rated(self) -> bool:
        """Check if module has SIL rating."""
        return self.sil_rating is not None and self.sil_rating != SILRating.NONE


@dataclass
class IOCard:
    """Represents an allocated I/O card instance."""
    module: IOModule             # Reference to module specification
    card_number: int             # Card instance number (1, 2, 3...)
    system: ControlSystem        # Which system this card belongs to
    location: str                # Cabinet/rack location

    # Allocation tracking
    total_channels: int = 0      # Module's channel count
    used_channels: int = 0       # Channels actually used
    spare_channels: int = 0      # Spare channels

    # Channel assignments
    channel_assignments: Dict[int, str] = field(default_factory=dict)  # channel_num -> instrument_tag

    @property
    def utilization_percent(self) -> float:
        """Calculate channel utilization percentage."""
        if self.total_channels == 0:
            return 0.0
        return (self.used_channels / self.total_channels) * 100

    @property
    def spare_percent(self) -> float:
        """Calculate spare capacity percentage."""
        if self.total_channels == 0:
            return 0.0
        return (self.spare_channels / self.total_channels) * 100


@dataclass
class Controller:
    """Represents a controller (FCS, SCS, RTU)."""
    model: str                   # e.g., "AFV30D", "SSC60D"
    tag_number: str              # e.g., "PP01-601-FCS001"
    system: ControlSystem
    location: str                # e.g., "CCR", "DS-1"

    # Specifications
    max_io_points: int = 0
    max_io_nodes: int = 0
    redundancy: bool = False
    sil_rating: Optional[SILRating] = None

    # Associated I/O cards
    io_cards: List[IOCard] = field(default_factory=list)

    @property
    def total_io_points(self) -> int:
        """Total I/O points from all cards."""
        return sum(card.total_channels for card in self.io_cards)

    @property
    def used_io_points(self) -> int:
        """Used I/O points from all cards."""
        return sum(card.used_channels for card in self.io_cards)


@dataclass
class IOAllocationResult:
    """Complete I/O allocation result for a project."""
    # Summary counts by system
    dcs_summary: Dict[str, int] = field(default_factory=dict)  # {AI: 85, AO: 15, ...}
    sis_summary: Dict[str, int] = field(default_factory=dict)
    rtu_summary: Dict[str, int] = field(default_factory=dict)

    # Card allocations
    dcs_cards: List[IOCard] = field(default_factory=list)
    sis_cards: List[IOCard] = field(default_factory=list)
    rtu_cards: List[IOCard] = field(default_factory=list)

    # Controllers
    controllers: List[Controller] = field(default_factory=list)

    # Spare capacity tracking
    spare_percent_target: float = 20.0
    actual_spare_percent: Dict[str, float] = field(default_factory=dict)

    # Segregation applied
    segregation_rules_applied: List[str] = field(default_factory=list)

    @property
    def total_cards(self) -> int:
        """Total number of I/O cards allocated."""
        return len(self.dcs_cards) + len(self.sis_cards) + len(self.rtu_cards)

    @property
    def all_cards(self) -> List[IOCard]:
        """All cards from all systems."""
        return self.dcs_cards + self.sis_cards + self.rtu_cards

    def get_cards_by_type(self, system: ControlSystem) -> List[IOCard]:
        """Get cards for a specific system."""
        if system == ControlSystem.DCS:
            return self.dcs_cards
        elif system == ControlSystem.SIS:
            return self.sis_cards
        elif system == ControlSystem.RTU:
            return self.rtu_cards
        return []

    def get_summary(self, system: ControlSystem) -> Dict[str, int]:
        """Get summary for a specific system."""
        if system == ControlSystem.DCS:
            return self.dcs_summary
        elif system == ControlSystem.SIS:
            return self.sis_summary
        elif system == ControlSystem.RTU:
            return self.rtu_summary
        return {}
