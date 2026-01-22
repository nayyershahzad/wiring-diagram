"""Cable data model for DCS interconnection diagrams."""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class CableType(Enum):
    """Cable type classification."""
    BRANCH = "BRANCH"           # Instrument to JB
    MULTIPAIR = "MULTIPAIR"     # JB to Marshalling Cabinet


@dataclass
class Cable:
    """Represents a cable in the interconnection system."""

    tag_number: str              # e.g., "PP01-601-I0004"
    cable_type: CableType        # BRANCH or MULTIPAIR
    specification: str           # "1Px1.5mm2", "5PRx1.0mm2", etc.
    pair_count: int              # Number of pairs
    from_location: str           # Source (Instrument or JB)
    to_location: str             # Destination (JB or Cabinet)
    length_meters: Optional[float] = None  # Cable length

    @property
    def is_branch(self) -> bool:
        """Check if cable is a branch cable."""
        return self.cable_type == CableType.BRANCH

    @property
    def is_multipair(self) -> bool:
        """Check if cable is a multipair cable."""
        return self.cable_type == CableType.MULTIPAIR

    @property
    def display_spec(self) -> str:
        """Get display-friendly specification."""
        return self.specification


@dataclass
class BranchCable(Cable):
    """Branch cable from instrument to junction box."""

    instrument_tag: Optional[str] = None  # Associated instrument

    def __post_init__(self):
        self.cable_type = CableType.BRANCH


@dataclass
class MultipairCable(Cable):
    """Multipair cable from junction box to marshalling cabinet."""

    used_pairs: int = 0          # Number of pairs in use
    spare_pairs: int = 0         # Number of spare pairs
    terminal_block_tag: Optional[str] = None  # Associated TB in cabinet

    def __post_init__(self):
        self.cable_type = CableType.MULTIPAIR

    @property
    def utilization_percent(self) -> float:
        """Calculate cable utilization percentage."""
        if self.pair_count == 0:
            return 0.0
        return (self.used_pairs / self.pair_count) * 100

    @property
    def spare_percent(self) -> float:
        """Calculate spare percentage."""
        if self.pair_count == 0:
            return 0.0
        return (self.spare_pairs / self.pair_count) * 100


# Multipair cable size options
MULTIPAIR_SIZES = [5, 10, 20]


# ============================================================================
# CABLE SPECIFICATIONS - Based on Industry Standards (BS5308, IEC, etc.)
# ============================================================================
#
# ANALOG SIGNALS (4-20mA):
# - Require Individually Shielded Twisted Pair (ISTP) for noise immunity
# - Conductor size: 1.5mm² (for longer runs and lower voltage drop)
# - Shield: Aluminum/Mylar with drain wire, grounded at control room end only
# - Multipair: Individually Shielded Pairs (ISP) with Overall Shield
#
# DIGITAL SIGNALS (24VDC):
# - Can use simpler Overall Shielded (OS) cables
# - Conductor size: 1.0mm² or 1.5mm² (less critical than analog)
# - Shield: Overall aluminum/mylar or braid
# - More tolerant to noise due to discrete nature
#
# RTD/THERMOCOUPLE:
# - RTD 3-wire: 3-core cable with individual shield
# - RTD 4-wire: 2-pair cable with individual shields
# - Thermocouple: Compensating cable matched to thermocouple type
#
# Sources:
# - BS5308 Part 1 & 2 Instrumentation Cables
# - IEC 60502-1 for cable construction
# - ISA standards for instrumentation wiring
# ============================================================================

# Branch cable specifications by signal type
CABLE_SPECIFICATIONS = {
    # Analog signals - Individually Shielded Twisted Pair (ISTP)
    "ANALOG_INPUT": {
        "specification": "1Px1.5mm²/ISTP",
        "full_spec": "1 Pair x 1.5mm² Individually Shielded Twisted Pair",
        "pair_count": 1,
        "conductor_size_mm2": 1.5,
        "shielding": "Individual aluminum/mylar + drain wire",
        "insulation": "XLPE",
        "notes": "4-20mA signal, shield grounded at DCS end only"
    },
    "ANALOG_OUTPUT": {
        "specification": "1Px1.5mm²/ISTP",
        "full_spec": "1 Pair x 1.5mm² Individually Shielded Twisted Pair",
        "pair_count": 1,
        "conductor_size_mm2": 1.5,
        "shielding": "Individual aluminum/mylar + drain wire",
        "insulation": "XLPE",
        "notes": "4-20mA signal to control valve/positioner"
    },

    # Digital signals - Overall Shielded (OS) - simpler construction
    "DIGITAL_INPUT": {
        "specification": "1Px1.0mm²/OS",
        "full_spec": "1 Pair x 1.0mm² Overall Shielded",
        "pair_count": 1,
        "conductor_size_mm2": 1.0,
        "shielding": "Overall aluminum/mylar",
        "insulation": "PVC",
        "notes": "24VDC discrete signal from switches/contacts"
    },
    "DIGITAL_OUTPUT": {
        "specification": "1Px1.0mm²/OS",
        "full_spec": "1 Pair x 1.0mm² Overall Shielded",
        "pair_count": 1,
        "conductor_size_mm2": 1.0,
        "shielding": "Overall aluminum/mylar",
        "insulation": "PVC",
        "notes": "24VDC discrete signal to solenoids/relays"
    },

    # Temperature elements - special requirements
    "THERMOCOUPLE": {
        "specification": "1Px1.5mm²/TC-EXT",
        "full_spec": "1 Pair x 1.5mm² Thermocouple Extension",
        "pair_count": 1,
        "conductor_size_mm2": 1.5,
        "shielding": "Individual + overall shield",
        "insulation": "PTFE/FEP",
        "notes": "Compensating cable matched to TC type (K, J, etc.)"
    },
    "RTD_3WIRE": {
        "specification": "3Cx1.5mm²/ISTP",
        "full_spec": "3 Core x 1.5mm² Individually Shielded",
        "pair_count": 1,  # Treated as 1 allocation
        "conductor_size_mm2": 1.5,
        "shielding": "Individual shield",
        "insulation": "XLPE",
        "notes": "PT100 3-wire RTD connection"
    },
    "RTD_4WIRE": {
        "specification": "2Px1.5mm²/ISP",
        "full_spec": "2 Pair x 1.5mm² Individually Shielded Pairs",
        "pair_count": 2,  # Uses 2 terminal pairs
        "conductor_size_mm2": 1.5,
        "shielding": "Individually shielded pairs",
        "insulation": "XLPE",
        "notes": "PT100 4-wire RTD for high accuracy"
    },
}

# Multipair cable specifications - different for Analog vs Digital
MULTIPAIR_SPECS = {
    # Analog multipair - Individually Shielded Pairs (ISP) with Overall Shield
    "ANALOG": {
        "conductor_size_mm2": 1.0,
        "specification_template": "{pairs}PRx1.0mm²/ISP-OS",
        "full_spec_template": "{pairs} Pair x 1.0mm² Individually Shielded Pairs + Overall Shield",
        "shielding": "Individual pair shields + overall aluminum/mylar",
        "insulation": "XLPE",
        "notes": "For 4-20mA analog signals, BS5308 Part 1 Type 2"
    },
    # Digital multipair - Overall Shielded Only (simpler, lower cost)
    "DIGITAL": {
        "conductor_size_mm2": 0.75,
        "specification_template": "{pairs}PRx0.75mm²/OS",
        "full_spec_template": "{pairs} Pair x 0.75mm² Overall Shielded",
        "shielding": "Overall aluminum/mylar braid",
        "insulation": "PVC",
        "notes": "For 24VDC digital signals, BS5308 Part 1 Type 1"
    },
}


def get_multipair_spec(pair_count: int, signal_category: str = "ANALOG") -> dict:
    """
    Get multipair cable specification based on signal category.

    Args:
        pair_count: Number of pairs (5, 10, or 20)
        signal_category: "ANALOG" or "DIGITAL"

    Returns:
        Dictionary with specification details
    """
    base_spec = MULTIPAIR_SPECS.get(signal_category, MULTIPAIR_SPECS["ANALOG"])
    return {
        "specification": base_spec["specification_template"].format(pairs=pair_count),
        "full_spec": base_spec["full_spec_template"].format(pairs=pair_count),
        "conductor_size_mm2": base_spec["conductor_size_mm2"],
        "shielding": base_spec["shielding"],
        "pair_count": pair_count,
    }
