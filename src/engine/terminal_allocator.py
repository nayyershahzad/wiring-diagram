"""Terminal allocation engine for DCS interconnection diagram generator."""

import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..models import (
    Instrument,
    SignalType,
    TerminalAllocation,
    TerminalBlock,
    TerminalStatus,
    EquipmentLocation,
    JunctionBox,
    MarshallingCabinet,
)
from .classifier import classify_jb_type, JBType


class TerminalAllocationError(Exception):
    """Exception raised for terminal allocation errors."""
    pass


class JBSize(Enum):
    """Standard Junction Box sizes based on industry practice."""
    SMALL = 12       # Small JB - 12 instruments
    STANDARD = 24    # Standard JB - 24 instruments
    LARGE = 48       # Large JB - 48 instruments


# Standard JB capacities (instruments per JB before spare allocation)
JB_CAPACITIES = {
    JBSize.SMALL: 12,
    JBSize.STANDARD: 24,
    JBSize.LARGE: 48,
}


@dataclass
class JBAllocationPlan:
    """Plan for allocating instruments across multiple JBs."""
    total_instruments: int
    jb_size: JBSize
    jb_capacity: int  # Effective capacity after spare %
    num_jbs_needed: int
    instruments_per_jb: List[int]  # Number of instruments in each JB
    spare_percent: float


def calculate_jb_allocation_plan(
    instrument_count: int,
    spare_percent: float = 0.20,
    preferred_size: JBSize = None,
) -> JBAllocationPlan:
    """
    Calculate how many JBs are needed and how to distribute instruments.

    Args:
        instrument_count: Total number of instruments
        spare_percent: Target spare percentage (default 20%)
        preferred_size: Preferred JB size (auto-select if None)

    Returns:
        JBAllocationPlan with allocation details
    """
    if preferred_size:
        jb_size = preferred_size
    else:
        # Auto-select JB size based on instrument count
        if instrument_count <= 10:
            jb_size = JBSize.SMALL
        elif instrument_count <= 40:
            jb_size = JBSize.STANDARD
        else:
            jb_size = JBSize.LARGE

    # Calculate effective capacity (with spare)
    raw_capacity = JB_CAPACITIES[jb_size]
    effective_capacity = int(raw_capacity * (1 - spare_percent))

    # Calculate number of JBs needed
    num_jbs = math.ceil(instrument_count / effective_capacity)

    # Distribute instruments evenly across JBs
    instruments_per_jb = []
    remaining = instrument_count
    for i in range(num_jbs):
        # Distribute evenly, putting extra in earlier JBs
        count = math.ceil(remaining / (num_jbs - i))
        instruments_per_jb.append(count)
        remaining -= count

    return JBAllocationPlan(
        total_instruments=instrument_count,
        jb_size=jb_size,
        jb_capacity=effective_capacity,
        num_jbs_needed=num_jbs,
        instruments_per_jb=instruments_per_jb,
        spare_percent=spare_percent,
    )


def suggest_jb_configuration(
    instruments: List[Instrument],
    spare_percent: float = 0.20,
) -> Dict:
    """
    Suggest JB configuration for a list of instruments.

    Args:
        instruments: List of instruments
        spare_percent: Target spare percentage

    Returns:
        Dictionary with configuration suggestions
    """
    count = len(instruments)

    suggestions = {}
    for size in JBSize:
        plan = calculate_jb_allocation_plan(count, spare_percent, size)
        suggestions[size.name] = {
            'jb_size': size.value,
            'num_jbs': plan.num_jbs_needed,
            'effective_capacity': plan.jb_capacity,
            'instruments_per_jb': plan.instruments_per_jb,
            'total_terminals': sum(
                math.ceil(n * (1 + spare_percent)) for n in plan.instruments_per_jb
            ),
        }

    # Recommend the most efficient option
    recommended = min(suggestions.items(), key=lambda x: x[1]['num_jbs'])

    return {
        'instrument_count': count,
        'spare_percent': spare_percent,
        'options': suggestions,
        'recommended': recommended[0],
        'recommended_details': recommended[1],
    }


@dataclass
class AllocationResult:
    """Result of terminal allocation."""
    terminal_block: TerminalBlock
    allocations: List[TerminalAllocation]
    used_count: int
    spare_count: int
    total_count: int

    @property
    def spare_percent(self) -> float:
        if self.total_count == 0:
            return 0.0
        return (self.spare_count / self.total_count) * 100


def calculate_terminals_needed(
    instrument_count: int,
    spare_percent: float = 0.20
) -> Tuple[int, int]:
    """
    Calculate the number of terminals needed including spares.

    Args:
        instrument_count: Number of instruments
        spare_percent: Target spare percentage

    Returns:
        Tuple of (total_terminals, spare_count)
    """
    spare_count = math.ceil(instrument_count * spare_percent)
    total = instrument_count + spare_count
    return total, spare_count


def allocate_jb_terminals(
    instruments: List[Instrument],
    jb_tag: str,
    spare_percent: float = 0.20,
    max_terminals: int = 48,  # Default to large JB capacity
    jb_size: JBSize = None,
) -> AllocationResult:
    """
    Allocate JB terminals for instruments with spare capacity.

    Terminal naming convention:
    - Signal terminals: 1+, 1-, 2+, 2-, ... (for each pair)
    - Shield terminals: 1S, 2S, 3S, ... (one per instrument)
    - Overall shield: 0S (connected to earth bar)

    Args:
        instruments: List of instruments to allocate
        jb_tag: Junction box tag
        spare_percent: Target spare percentage (default 20%)
        max_terminals: Maximum terminals per JB (default 48 for large JB)
        jb_size: Optional JBSize enum to specify JB size

    Returns:
        AllocationResult with terminal allocations

    Raises:
        TerminalAllocationError: If too many instruments for specified JB size
    """
    total_instruments = len(instruments)
    total_needed, spare_count = calculate_terminals_needed(total_instruments, spare_percent)

    # Use JB size if specified, otherwise use max_terminals
    if jb_size:
        max_terminals = JB_CAPACITIES[jb_size]

    if total_needed > max_terminals:
        # Calculate how many JBs would be needed
        plan = calculate_jb_allocation_plan(total_instruments, spare_percent)
        raise TerminalAllocationError(
            f"Too many instruments ({total_instruments}) for single JB (max {max_terminals}). "
            f"Recommend using {plan.num_jbs_needed} x {plan.jb_size.name} JBs "
            f"({plan.jb_size.value} terminals each). "
            f"Use allocate_multiple_jbs() for automatic multi-JB allocation."
        )

    allocations = []

    # Allocate terminals for each instrument
    for idx, instrument in enumerate(instruments, start=1):
        allocation = TerminalAllocation(
            terminal_number=idx,
            terminal_positive=f"{idx}+",
            terminal_negative=f"{idx}-",
            terminal_shield=f"{idx}S",
            instrument_tag=instrument.tag_number,
            dcs_tag=instrument.tag_number,
            status=TerminalStatus.USED,
        )
        allocations.append(allocation)

        # Update instrument with terminal assignments
        instrument.jb_terminal_positive = f"{idx}+"
        instrument.jb_terminal_negative = f"{idx}-"
        instrument.jb_terminal_shield = f"{idx}S"

    # Add spare terminals
    for idx in range(total_instruments + 1, total_needed + 1):
        allocation = TerminalAllocation(
            terminal_number=idx,
            terminal_positive=f"{idx}+",
            terminal_negative=f"{idx}-",
            terminal_shield=f"{idx}S",
            instrument_tag="SPARE",
            status=TerminalStatus.SPARE,
        )
        allocations.append(allocation)

    # Create terminal block
    terminal_block = TerminalBlock(
        tag_number=f"TB-{jb_tag}",
        location=EquipmentLocation.JUNCTION_BOX,
        parent_equipment=jb_tag,
        total_terminals=total_needed,
        allocations=allocations,
    )

    return AllocationResult(
        terminal_block=terminal_block,
        allocations=allocations,
        used_count=total_instruments,
        spare_count=spare_count,
        total_count=total_needed,
    )


def allocate_cabinet_terminals(
    instruments: List[Instrument],
    cabinet_tag: str,
    tb_tag: str,
    spare_percent: float = 0.20,
    max_pairs: int = 20
) -> AllocationResult:
    """
    Allocate marshalling cabinet terminals with spare capacity.

    Terminal naming convention:
    - Terminal block pairs: PR1, PR2, PR3, ... PR20 (max 20 per TB)
    - Each PRx has: x+, x- for signal
    - Wire colors: WH (White) for positive, BK (Black) for negative
    - Overall shield: 0S (to instrument earth bar)

    Args:
        instruments: List of instruments to allocate
        cabinet_tag: Marshalling cabinet tag
        tb_tag: Terminal block tag
        spare_percent: Target spare percentage
        max_pairs: Maximum pairs per terminal block

    Returns:
        AllocationResult with terminal allocations

    Raises:
        TerminalAllocationError: If too many instruments for single TB
    """
    total_instruments = len(instruments)
    total_needed, spare_count = calculate_terminals_needed(total_instruments, spare_percent)

    if total_needed > max_pairs:
        raise TerminalAllocationError(
            f"Too many instruments ({total_instruments}) for single terminal block. "
            f"Maximum capacity with {spare_percent*100:.0f}% spare: "
            f"{int(max_pairs * (1 - spare_percent))}"
        )

    allocations = []

    # Allocate terminals for each instrument
    for idx, instrument in enumerate(instruments, start=1):
        allocation = TerminalAllocation(
            terminal_number=idx,
            terminal_pair=f"PR{idx}",
            terminal_positive=f"{idx}+",
            terminal_negative=f"{idx}-",
            wire_color_positive="WH",
            wire_color_negative="BK",
            instrument_tag=instrument.tag_number,
            dcs_tag=instrument.tag_number,
            status=TerminalStatus.USED,
        )
        allocations.append(allocation)

        # Update instrument with cabinet terminal assignments
        instrument.cabinet_terminal_pair = f"PR{idx}"
        instrument.cabinet_terminal_positive = f"{idx}+"
        instrument.cabinet_terminal_negative = f"{idx}-"

    # Add spare terminals
    for idx in range(total_instruments + 1, total_needed + 1):
        allocation = TerminalAllocation(
            terminal_number=idx,
            terminal_pair=f"PR{idx}",
            terminal_positive=f"{idx}+",
            terminal_negative=f"{idx}-",
            wire_color_positive="WH",
            wire_color_negative="BK",
            instrument_tag="SPARE",
            status=TerminalStatus.SPARE,
        )
        allocations.append(allocation)

    # Create terminal block
    terminal_block = TerminalBlock(
        tag_number=tb_tag,
        location=EquipmentLocation.MARSHALLING_CABINET,
        parent_equipment=cabinet_tag,
        total_terminals=total_needed,
        allocations=allocations,
    )

    return AllocationResult(
        terminal_block=terminal_block,
        allocations=allocations,
        used_count=total_instruments,
        spare_count=spare_count,
        total_count=total_needed,
    )


def create_junction_box(
    jb_tag: str,
    instruments: List[Instrument],
    multipair_cable_tag: str,
    spare_percent: float = 0.20,
) -> Tuple[JunctionBox, AllocationResult]:
    """
    Create a junction box with terminal allocations.

    Args:
        jb_tag: Junction box tag
        instruments: List of instruments
        multipair_cable_tag: Associated multipair cable tag
        spare_percent: Target spare percentage

    Returns:
        Tuple of (JunctionBox, AllocationResult)
    """
    # Determine JB type
    jb_type = classify_jb_type(instruments)

    # Parse area from JB tag (e.g., PP01-601-IAJB0002 -> 601)
    parts = jb_tag.split("-")
    area = parts[1] if len(parts) >= 2 else "000"

    # Allocate terminals
    allocation_result = allocate_jb_terminals(
        instruments=instruments,
        jb_tag=jb_tag,
        spare_percent=spare_percent,
    )

    # Create JB
    jb = JunctionBox(
        tag_number=jb_tag,
        jb_type=jb_type.value,
        area=area,
        terminal_block=allocation_result.terminal_block,
        multipair_cable_tag=multipair_cable_tag,
    )

    return jb, allocation_result


def create_marshalling_cabinet(
    cabinet_tag: str,
    terminal_blocks: List[TerminalBlock] = None,
) -> MarshallingCabinet:
    """
    Create a marshalling cabinet.

    Args:
        cabinet_tag: Cabinet tag
        terminal_blocks: Optional list of terminal blocks

    Returns:
        MarshallingCabinet object
    """
    # Parse area from cabinet tag
    parts = cabinet_tag.split("-")
    area = parts[1] if len(parts) >= 2 else "000"

    return MarshallingCabinet(
        tag_number=cabinet_tag,
        area=area,
        terminal_blocks=terminal_blocks or [],
    )


def allocate_all_terminals(
    instruments: List[Instrument],
    jb_tag: str,
    cabinet_tag: str,
    tb_tag: str,
    multipair_cable_tag: str,
    spare_percent: float = 0.20,
) -> Dict:
    """
    Allocate all terminals for a complete JB-to-Cabinet connection.

    Args:
        instruments: List of instruments
        jb_tag: Junction box tag
        cabinet_tag: Marshalling cabinet tag
        tb_tag: Terminal block tag
        multipair_cable_tag: Multipair cable tag
        spare_percent: Target spare percentage

    Returns:
        Dictionary with JB, cabinet, and allocation results
    """
    # Create JB with terminals
    jb, jb_allocation = create_junction_box(
        jb_tag=jb_tag,
        instruments=instruments,
        multipair_cable_tag=multipair_cable_tag,
        spare_percent=spare_percent,
    )

    # Allocate cabinet terminals
    cabinet_allocation = allocate_cabinet_terminals(
        instruments=instruments,
        cabinet_tag=cabinet_tag,
        tb_tag=tb_tag,
        spare_percent=spare_percent,
    )

    # Create cabinet
    cabinet = create_marshalling_cabinet(
        cabinet_tag=cabinet_tag,
        terminal_blocks=[cabinet_allocation.terminal_block],
    )

    return {
        "junction_box": jb,
        "jb_allocation": jb_allocation,
        "cabinet": cabinet,
        "cabinet_allocation": cabinet_allocation,
        "instruments": instruments,
    }


@dataclass
class MultiJBAllocationResult:
    """Result of allocating instruments across multiple JBs."""
    plan: JBAllocationPlan
    junction_boxes: List[JunctionBox]
    jb_allocations: List[AllocationResult]
    instrument_assignments: Dict[str, str]  # instrument_tag -> jb_tag


def allocate_multiple_jbs(
    instruments: List[Instrument],
    base_jb_tag: str,
    multipair_cable_base_tag: str,
    spare_percent: float = 0.20,
    preferred_size: JBSize = None,
) -> MultiJBAllocationResult:
    """
    Automatically allocate instruments across multiple JBs as needed.

    This function calculates the optimal number of JBs based on instrument count
    and distributes instruments evenly across them.

    Args:
        instruments: List of all instruments to allocate
        base_jb_tag: Base JB tag (will be suffixed with A, B, C, etc. for multiple JBs)
                     e.g., "PP01-601-IAJB0002" becomes "PP01-601-IAJB0002A", "PP01-601-IAJB0002B"
        multipair_cable_base_tag: Base multipair cable tag (will be suffixed similarly)
        spare_percent: Target spare percentage (default 20%)
        preferred_size: Preferred JB size (auto-select if None)

    Returns:
        MultiJBAllocationResult with all JBs and their allocations

    Example:
        >>> result = allocate_multiple_jbs(instruments, "PP01-601-IAJB0002", "PP01-601-I0004")
        >>> print(f"Need {len(result.junction_boxes)} JBs")
        >>> for jb in result.junction_boxes:
        >>>     print(f"  {jb.tag_number}: {len(jb.terminal_block.allocations)} terminals")
    """
    total_count = len(instruments)

    # Calculate allocation plan
    plan = calculate_jb_allocation_plan(total_count, spare_percent, preferred_size)

    junction_boxes = []
    jb_allocations = []
    instrument_assignments = {}

    # Split instruments according to plan
    start_idx = 0
    suffixes = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    for jb_idx, inst_count in enumerate(plan.instruments_per_jb):
        # Get instruments for this JB
        end_idx = start_idx + inst_count
        jb_instruments = instruments[start_idx:end_idx]
        start_idx = end_idx

        # Generate JB tag with suffix if multiple JBs
        if plan.num_jbs_needed > 1:
            suffix = suffixes[jb_idx] if jb_idx < len(suffixes) else str(jb_idx + 1)
            jb_tag = f"{base_jb_tag}{suffix}"
            cable_tag = f"{multipair_cable_base_tag}{suffix}"
        else:
            jb_tag = base_jb_tag
            cable_tag = multipair_cable_base_tag

        # Create JB with terminals
        jb, allocation = create_junction_box(
            jb_tag=jb_tag,
            instruments=jb_instruments,
            multipair_cable_tag=cable_tag,
            spare_percent=spare_percent,
        )

        junction_boxes.append(jb)
        jb_allocations.append(allocation)

        # Track which instruments are in which JB
        for inst in jb_instruments:
            instrument_assignments[inst.tag_number] = jb_tag

    return MultiJBAllocationResult(
        plan=plan,
        junction_boxes=junction_boxes,
        jb_allocations=jb_allocations,
        instrument_assignments=instrument_assignments,
    )


def allocate_all_terminals_auto(
    instruments: List[Instrument],
    base_jb_tag: str,
    cabinet_tag: str,
    base_tb_tag: str,
    base_multipair_cable_tag: str,
    spare_percent: float = 0.20,
    preferred_jb_size: JBSize = None,
) -> Dict:
    """
    Automatically allocate all terminals, splitting across multiple JBs if needed.

    This is the recommended function for handling any number of instruments.
    It automatically determines the optimal number of JBs and creates
    corresponding terminal blocks in the marshalling cabinet.

    Args:
        instruments: List of instruments
        base_jb_tag: Base junction box tag
        cabinet_tag: Marshalling cabinet tag
        base_tb_tag: Base terminal block tag
        base_multipair_cable_tag: Base multipair cable tag
        spare_percent: Target spare percentage
        preferred_jb_size: Preferred JB size (auto-select if None)

    Returns:
        Dictionary with all JBs, cabinet, and allocation results
    """
    # Allocate across multiple JBs
    multi_jb_result = allocate_multiple_jbs(
        instruments=instruments,
        base_jb_tag=base_jb_tag,
        multipair_cable_base_tag=base_multipair_cable_tag,
        spare_percent=spare_percent,
        preferred_size=preferred_jb_size,
    )

    # Create cabinet terminal blocks for each JB
    cabinet_terminal_blocks = []
    cabinet_allocations = []
    suffixes = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    start_idx = 0
    for jb_idx, jb in enumerate(multi_jb_result.junction_boxes):
        # Get instruments for this JB
        inst_count = multi_jb_result.plan.instruments_per_jb[jb_idx]
        end_idx = start_idx + inst_count
        jb_instruments = instruments[start_idx:end_idx]
        start_idx = end_idx

        # Generate TB tag
        if multi_jb_result.plan.num_jbs_needed > 1:
            suffix = suffixes[jb_idx] if jb_idx < len(suffixes) else str(jb_idx + 1)
            tb_tag = f"{base_tb_tag}{suffix}"
        else:
            tb_tag = base_tb_tag

        # Allocate cabinet terminals
        cabinet_allocation = allocate_cabinet_terminals(
            instruments=jb_instruments,
            cabinet_tag=cabinet_tag,
            tb_tag=tb_tag,
            spare_percent=spare_percent,
            max_pairs=JB_CAPACITIES[multi_jb_result.plan.jb_size],
        )

        cabinet_terminal_blocks.append(cabinet_allocation.terminal_block)
        cabinet_allocations.append(cabinet_allocation)

    # Create cabinet
    cabinet = create_marshalling_cabinet(
        cabinet_tag=cabinet_tag,
        terminal_blocks=cabinet_terminal_blocks,
    )

    return {
        "multi_jb_result": multi_jb_result,
        "junction_boxes": multi_jb_result.junction_boxes,
        "jb_allocations": multi_jb_result.jb_allocations,
        "cabinet": cabinet,
        "cabinet_allocations": cabinet_allocations,
        "cabinet_terminal_blocks": cabinet_terminal_blocks,
        "instruments": instruments,
        "instrument_assignments": multi_jb_result.instrument_assignments,
        "plan": multi_jb_result.plan,
        "num_jbs": multi_jb_result.plan.num_jbs_needed,
    }


# ============================================================================
# SIGNAL TYPE SEGREGATION - Industry Best Practice
# ============================================================================
# Per industry standards, Analog and Digital signals should be segregated:
# - Analog JBs (IAJB): For 4-20mA signals (AI/AO, RTD, TC)
# - Digital JBs (IDJB): For 24VDC discrete signals (DI/DO)
#
# This prevents cross-talk and interference between signal types.
# ============================================================================

# Analog signal types
ANALOG_SIGNAL_TYPES = {
    SignalType.ANALOG_INPUT,
    SignalType.ANALOG_OUTPUT,
    SignalType.THERMOCOUPLE,
    SignalType.RTD_3WIRE,
    SignalType.RTD_4WIRE,
}

# Digital signal types
DIGITAL_SIGNAL_TYPES = {
    SignalType.DIGITAL_INPUT,
    SignalType.DIGITAL_OUTPUT,
}


def separate_instruments_by_signal_type(
    instruments: List[Instrument]
) -> Dict[str, List[Instrument]]:
    """
    Separate instruments into Analog and Digital groups.

    This follows industry best practice of segregating signal types
    to prevent cross-talk and interference.

    Args:
        instruments: List of all instruments

    Returns:
        Dictionary with 'ANALOG' and 'DIGITAL' instrument lists
    """
    analog_instruments = []
    digital_instruments = []

    for inst in instruments:
        if inst.signal_type in ANALOG_SIGNAL_TYPES:
            analog_instruments.append(inst)
        elif inst.signal_type in DIGITAL_SIGNAL_TYPES:
            digital_instruments.append(inst)
        else:
            # Default unknown types to analog (safer)
            analog_instruments.append(inst)

    return {
        "ANALOG": analog_instruments,
        "DIGITAL": digital_instruments,
    }


@dataclass
class SignalTypeAllocationResult:
    """Result of signal-type-segregated allocation."""
    analog_jbs: List[JunctionBox]
    digital_jbs: List[JunctionBox]
    all_jbs: List[JunctionBox]
    analog_instruments: List[Instrument]
    digital_instruments: List[Instrument]
    analog_plan: Optional[JBAllocationPlan]
    digital_plan: Optional[JBAllocationPlan]
    total_analog_jbs: int
    total_digital_jbs: int


def allocate_by_signal_type(
    instruments: List[Instrument],
    base_analog_jb_tag: str,
    base_digital_jb_tag: str,
    cabinet_tag: str,
    base_analog_cable_tag: str,
    base_digital_cable_tag: str,
    base_analog_tb_tag: str,
    base_digital_tb_tag: str,
    spare_percent: float = 0.20,
) -> Dict:
    """
    Allocate instruments to separate Analog and Digital JBs.

    This is the recommended function for proper signal segregation.
    It automatically:
    1. Separates instruments by signal type (Analog vs Digital)
    2. Creates separate JBs for each signal type
    3. Uses appropriate cable specifications for each type

    Args:
        instruments: List of all instruments
        base_analog_jb_tag: Base tag for analog JBs (e.g., "PP01-601-IAJB0001")
        base_digital_jb_tag: Base tag for digital JBs (e.g., "PP01-601-IDJB0001")
        cabinet_tag: Marshalling cabinet tag
        base_analog_cable_tag: Base multipair cable tag for analog
        base_digital_cable_tag: Base multipair cable tag for digital
        base_analog_tb_tag: Base terminal block tag for analog
        base_digital_tb_tag: Base terminal block tag for digital
        spare_percent: Target spare percentage

    Returns:
        Dictionary with complete allocation results for both signal types

    Example:
        >>> result = allocate_by_signal_type(
        ...     instruments,
        ...     base_analog_jb_tag="PP01-601-IAJB0001",
        ...     base_digital_jb_tag="PP01-601-IDJB0001",
        ...     cabinet_tag="PP01-601-ICP001",
        ...     base_analog_cable_tag="PP01-601-I0001",
        ...     base_digital_cable_tag="PP01-601-I0050",
        ...     base_analog_tb_tag="TB601-I0001",
        ...     base_digital_tb_tag="TB601-I0050",
        ... )
        >>> print(f"Analog: {result['analog_count']} instruments in {result['analog_jb_count']} JBs")
        >>> print(f"Digital: {result['digital_count']} instruments in {result['digital_jb_count']} JBs")
    """
    # Separate instruments by signal type
    separated = separate_instruments_by_signal_type(instruments)
    analog_instruments = separated["ANALOG"]
    digital_instruments = separated["DIGITAL"]

    result = {
        "analog_instruments": analog_instruments,
        "digital_instruments": digital_instruments,
        "analog_count": len(analog_instruments),
        "digital_count": len(digital_instruments),
        "analog_jbs": [],
        "digital_jbs": [],
        "all_jbs": [],
        "analog_jb_count": 0,
        "digital_jb_count": 0,
        "total_jb_count": 0,
    }

    # Allocate Analog JBs if there are analog instruments
    if analog_instruments:
        analog_result = allocate_all_terminals_auto(
            instruments=analog_instruments,
            base_jb_tag=base_analog_jb_tag,
            cabinet_tag=cabinet_tag,
            base_tb_tag=base_analog_tb_tag,
            base_multipair_cable_tag=base_analog_cable_tag,
            spare_percent=spare_percent,
        )
        result["analog_jbs"] = analog_result["junction_boxes"]
        result["analog_jb_count"] = analog_result["num_jbs"]
        result["analog_allocation"] = analog_result
        result["analog_plan"] = analog_result["plan"]
        result["all_jbs"].extend(analog_result["junction_boxes"])

    # Allocate Digital JBs if there are digital instruments
    if digital_instruments:
        digital_result = allocate_all_terminals_auto(
            instruments=digital_instruments,
            base_jb_tag=base_digital_jb_tag,
            cabinet_tag=cabinet_tag,
            base_tb_tag=base_digital_tb_tag,
            base_multipair_cable_tag=base_digital_cable_tag,
            spare_percent=spare_percent,
        )
        result["digital_jbs"] = digital_result["junction_boxes"]
        result["digital_jb_count"] = digital_result["num_jbs"]
        result["digital_allocation"] = digital_result
        result["digital_plan"] = digital_result["plan"]
        result["all_jbs"].extend(digital_result["junction_boxes"])

    result["total_jb_count"] = result["analog_jb_count"] + result["digital_jb_count"]

    return result


def get_signal_type_summary(instruments: List[Instrument]) -> Dict:
    """
    Get a summary of instruments by signal type.

    Useful for displaying to users before allocation.

    Args:
        instruments: List of instruments

    Returns:
        Dictionary with signal type breakdown
    """
    separated = separate_instruments_by_signal_type(instruments)

    analog_count = len(separated["ANALOG"])
    digital_count = len(separated["DIGITAL"])

    # Calculate JB requirements for each type
    analog_plan = None
    digital_plan = None

    if analog_count > 0:
        analog_plan = calculate_jb_allocation_plan(analog_count)

    if digital_count > 0:
        digital_plan = calculate_jb_allocation_plan(digital_count)

    return {
        "analog_count": analog_count,
        "digital_count": digital_count,
        "total_count": analog_count + digital_count,
        "analog_jbs_needed": analog_plan.num_jbs_needed if analog_plan else 0,
        "digital_jbs_needed": digital_plan.num_jbs_needed if digital_plan else 0,
        "total_jbs_needed": (
            (analog_plan.num_jbs_needed if analog_plan else 0) +
            (digital_plan.num_jbs_needed if digital_plan else 0)
        ),
        "analog_plan": analog_plan,
        "digital_plan": digital_plan,
        "signal_breakdown": {
            "ANALOG_INPUT": sum(1 for i in separated["ANALOG"] if i.signal_type == SignalType.ANALOG_INPUT),
            "ANALOG_OUTPUT": sum(1 for i in separated["ANALOG"] if i.signal_type == SignalType.ANALOG_OUTPUT),
            "DIGITAL_INPUT": sum(1 for i in separated["DIGITAL"] if i.signal_type == SignalType.DIGITAL_INPUT),
            "DIGITAL_OUTPUT": sum(1 for i in separated["DIGITAL"] if i.signal_type == SignalType.DIGITAL_OUTPUT),
            "RTD": sum(1 for i in separated["ANALOG"] if i.signal_type in {SignalType.RTD_3WIRE, SignalType.RTD_4WIRE}),
            "THERMOCOUPLE": sum(1 for i in separated["ANALOG"] if i.signal_type == SignalType.THERMOCOUPLE),
        }
    }
