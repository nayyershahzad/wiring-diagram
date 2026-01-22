"""Cable sizing engine for DCS interconnection diagram generator."""

import math
from typing import List, Optional, Tuple
from dataclasses import dataclass

from ..models import (
    Instrument,
    SignalType,
    Cable,
    CableType,
    BranchCable,
    MultipairCable,
    CABLE_SPECIFICATIONS,
    MULTIPAIR_SIZES,
    MULTIPAIR_SPECS,
    get_multipair_spec,
)


class CableSizingError(Exception):
    """Exception raised for cable sizing errors."""
    pass


@dataclass
class CableSizingResult:
    """Result of cable sizing calculation."""
    branch_cables: List[BranchCable]
    multipair_cable: MultipairCable
    total_pairs_needed: int
    spare_pairs: int
    spare_percent: float


def get_branch_cable_spec(signal_type: SignalType) -> Tuple[str, int]:
    """
    Get the cable specification for a branch cable based on signal type.

    Args:
        signal_type: SignalType enum value

    Returns:
        Tuple of (specification, pair_count)
    """
    spec_key = signal_type.value

    if spec_key in CABLE_SPECIFICATIONS:
        spec = CABLE_SPECIFICATIONS[spec_key]
        return spec["specification"], spec["pair_count"]

    # Default to single pair 1.5mm2
    return "1Px1.5mm2", 1


def create_branch_cable(
    instrument: Instrument,
    jb_tag: str,
    cable_tag: Optional[str] = None
) -> BranchCable:
    """
    Create a branch cable for an instrument.

    Args:
        instrument: The instrument to create cable for
        jb_tag: Junction box tag
        cable_tag: Optional cable tag (defaults to instrument tag)

    Returns:
        BranchCable object
    """
    specification, pair_count = get_branch_cable_spec(instrument.signal_type)

    return BranchCable(
        tag_number=cable_tag or instrument.tag_number,
        cable_type=CableType.BRANCH,
        specification=specification,
        pair_count=pair_count,
        from_location=instrument.tag_number,
        to_location=jb_tag,
        instrument_tag=instrument.tag_number,
    )


def calculate_multipair_size(
    instrument_count: int,
    spare_percent: float = 0.20
) -> int:
    """
    Calculate the required multipair cable size with spare capacity.

    Args:
        instrument_count: Number of instruments (pairs needed)
        spare_percent: Target spare percentage (default 20%)

    Returns:
        Selected multipair cable size (5, 10, or 20 pairs)

    Raises:
        CableSizingError: If requirements exceed maximum cable size
    """
    if instrument_count <= 0:
        return MULTIPAIR_SIZES[0]  # Minimum size

    required_with_spare = math.ceil(instrument_count * (1 + spare_percent))

    for size in MULTIPAIR_SIZES:
        if size >= required_with_spare:
            return size

    # If more than 20 pairs needed, raise error (would need multiple cables)
    if required_with_spare > max(MULTIPAIR_SIZES):
        raise CableSizingError(
            f"Too many instruments ({instrument_count}) for single multipair cable. "
            f"Maximum capacity: {max(MULTIPAIR_SIZES)} pairs. "
            f"Required with spare: {required_with_spare} pairs."
        )

    return max(MULTIPAIR_SIZES)


def get_multipair_specification(pair_count: int, signal_category: str = "ANALOG") -> str:
    """
    Get the cable specification string for a multipair cable.

    Args:
        pair_count: Number of pairs (5, 10, or 20)
        signal_category: "ANALOG" or "DIGITAL" for correct cable type

    Returns:
        Specification string based on signal category:
        - Analog: "5PRx1.0mm²/ISP-OS" (Individually Shielded Pairs + Overall Shield)
        - Digital: "5PRx0.75mm²/OS" (Overall Shielded only)
    """
    spec = get_multipair_spec(pair_count, signal_category)
    return spec["specification"]


def determine_signal_category(instruments: List[Instrument]) -> str:
    """
    Determine the signal category (ANALOG or DIGITAL) based on instruments.

    Args:
        instruments: List of instruments

    Returns:
        "ANALOG" or "DIGITAL" based on majority of signals
    """
    if not instruments:
        return "ANALOG"

    analog_types = {
        SignalType.ANALOG_INPUT,
        SignalType.ANALOG_OUTPUT,
        SignalType.THERMOCOUPLE,
        SignalType.RTD_3WIRE,
        SignalType.RTD_4WIRE
    }

    analog_count = sum(1 for inst in instruments if inst.signal_type in analog_types)
    digital_count = len(instruments) - analog_count

    return "ANALOG" if analog_count >= digital_count else "DIGITAL"


def create_multipair_cable(
    jb_tag: str,
    cabinet_tag: str,
    cable_tag: str,
    instrument_count: int,
    spare_percent: float = 0.20,
    signal_category: str = "ANALOG"
) -> MultipairCable:
    """
    Create a multipair cable from JB to cabinet.

    Args:
        jb_tag: Junction box tag
        cabinet_tag: Marshalling cabinet tag
        cable_tag: Cable tag number
        instrument_count: Number of instruments
        spare_percent: Target spare percentage
        signal_category: "ANALOG" or "DIGITAL" for correct cable specification

    Returns:
        MultipairCable object with appropriate cable specification
    """
    pair_count = calculate_multipair_size(instrument_count, spare_percent)
    spare_pairs = pair_count - instrument_count
    actual_spare_percent = spare_pairs / pair_count if pair_count > 0 else 0

    return MultipairCable(
        tag_number=cable_tag,
        cable_type=CableType.MULTIPAIR,
        specification=get_multipair_specification(pair_count, signal_category),
        pair_count=pair_count,
        from_location=jb_tag,
        to_location=cabinet_tag,
        used_pairs=instrument_count,
        spare_pairs=spare_pairs,
    )


def size_cables_for_jb(
    instruments: List[Instrument],
    jb_tag: str,
    cabinet_tag: str,
    multipair_cable_tag: str,
    spare_percent: float = 0.20,
    signal_category: str = None
) -> CableSizingResult:
    """
    Size all cables for a junction box.

    This creates branch cables for each instrument and calculates
    the appropriate multipair cable size with correct specification
    based on signal type (Analog or Digital).

    Args:
        instruments: List of instruments connected to the JB
        jb_tag: Junction box tag
        cabinet_tag: Marshalling cabinet tag
        multipair_cable_tag: Tag for the multipair cable
        spare_percent: Target spare percentage
        signal_category: "ANALOG" or "DIGITAL" (auto-detected if None)

    Returns:
        CableSizingResult with all cable information

    Notes:
        - Analog signals use Individually Shielded Pairs (ISP) with
          Overall Shield, 1.0mm² conductors
        - Digital signals use Overall Shielded (OS) only, 0.75mm² conductors
    """
    # Create branch cables for each instrument
    branch_cables = [
        create_branch_cable(inst, jb_tag)
        for inst in instruments
    ]

    # Calculate total pairs needed (considering RTD 4-wire needs 2 pairs)
    total_pairs = sum(cable.pair_count for cable in branch_cables)

    # Determine signal category if not provided
    if signal_category is None:
        signal_category = determine_signal_category(instruments)

    # Create multipair cable with appropriate specification
    multipair_cable = create_multipair_cable(
        jb_tag=jb_tag,
        cabinet_tag=cabinet_tag,
        cable_tag=multipair_cable_tag,
        instrument_count=total_pairs,
        spare_percent=spare_percent,
        signal_category=signal_category
    )

    return CableSizingResult(
        branch_cables=branch_cables,
        multipair_cable=multipair_cable,
        total_pairs_needed=total_pairs,
        spare_pairs=multipair_cable.spare_pairs,
        spare_percent=multipair_cable.spare_percent,
    )


def calculate_multiple_multipairs(
    instrument_count: int,
    spare_percent: float = 0.20
) -> List[int]:
    """
    Calculate multiple multipair cable sizes when one is not enough.

    Args:
        instrument_count: Total number of instruments
        spare_percent: Target spare percentage

    Returns:
        List of cable sizes (e.g., [20, 10] for 25 instruments)
    """
    required_with_spare = math.ceil(instrument_count * (1 + spare_percent))
    cables = []
    remaining = required_with_spare

    # Use largest cables first
    for size in sorted(MULTIPAIR_SIZES, reverse=True):
        while remaining >= size:
            cables.append(size)
            remaining -= size

    # Add one more cable for remaining if needed
    if remaining > 0:
        for size in MULTIPAIR_SIZES:
            if size >= remaining:
                cables.append(size)
                break

    return cables
