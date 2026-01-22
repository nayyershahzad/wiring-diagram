"""Instrument and JB type classifier for DCS interconnection diagram generator."""

from typing import List, Set
from enum import Enum

from ..models import Instrument, SignalType


class JBType(Enum):
    """Junction Box type classification."""
    ANALOG = "ANALOG"
    DIGITAL = "DIGITAL"
    MIXED = "MIXED"


def classify_instrument(instrument_type: str) -> SignalType:
    """
    Classify an instrument by its type code.

    Args:
        instrument_type: Instrument type code (e.g., "TIT", "PIT", "ZS")

    Returns:
        SignalType enum value
    """
    from ..models.instrument import INSTRUMENT_CLASSIFICATION

    # Direct match
    if instrument_type in INSTRUMENT_CLASSIFICATION:
        return INSTRUMENT_CLASSIFICATION[instrument_type]

    # Prefix matching (longest prefix first)
    for prefix in sorted(INSTRUMENT_CLASSIFICATION.keys(), key=len, reverse=True):
        if instrument_type.startswith(prefix):
            return INSTRUMENT_CLASSIFICATION[prefix]

    # Default to analog input
    return SignalType.ANALOG_INPUT


def classify_jb_type(instruments: List[Instrument]) -> JBType:
    """
    Classify JB type based on the instruments connected to it.

    A JB is classified as:
    - ANALOG: All instruments are analog (AI, AO, TC, RTD)
    - DIGITAL: All instruments are digital (DI, DO)
    - MIXED: Contains both analog and digital instruments

    Args:
        instruments: List of instruments connected to the JB

    Returns:
        JBType enum value
    """
    if not instruments:
        return JBType.ANALOG  # Default

    signal_types: Set[SignalType] = {inst.signal_type for inst in instruments}

    analog_types = {
        SignalType.ANALOG_INPUT,
        SignalType.ANALOG_OUTPUT,
        SignalType.THERMOCOUPLE,
        SignalType.RTD_3WIRE,
        SignalType.RTD_4WIRE
    }

    digital_types = {
        SignalType.DIGITAL_INPUT,
        SignalType.DIGITAL_OUTPUT
    }

    has_analog = bool(signal_types & analog_types)
    has_digital = bool(signal_types & digital_types)

    if has_analog and has_digital:
        return JBType.MIXED
    elif has_digital:
        return JBType.DIGITAL
    else:
        return JBType.ANALOG


def get_jb_tag_prefix(jb_type: JBType) -> str:
    """
    Get the tag prefix for a JB based on its type.

    Args:
        jb_type: JBType enum value

    Returns:
        Tag prefix string ("IA" for analog, "ID" for digital, "IM" for mixed)
    """
    prefixes = {
        JBType.ANALOG: "IA",   # Instrument Analog
        JBType.DIGITAL: "ID",  # Instrument Digital
        JBType.MIXED: "IM"     # Instrument Mixed
    }
    return prefixes.get(jb_type, "IA")


def is_input_signal(signal_type: SignalType) -> bool:
    """Check if signal type is an input."""
    return signal_type in [
        SignalType.ANALOG_INPUT,
        SignalType.DIGITAL_INPUT,
        SignalType.THERMOCOUPLE,
        SignalType.RTD_3WIRE,
        SignalType.RTD_4WIRE
    ]


def is_output_signal(signal_type: SignalType) -> bool:
    """Check if signal type is an output."""
    return signal_type in [
        SignalType.ANALOG_OUTPUT,
        SignalType.DIGITAL_OUTPUT
    ]


def get_io_type_code(signal_type: SignalType) -> str:
    """
    Get the I/O type code for a signal type.

    Args:
        signal_type: SignalType enum value

    Returns:
        I/O type code string ("AI", "AO", "DI", "DO")
    """
    mapping = {
        SignalType.ANALOG_INPUT: "AI",
        SignalType.ANALOG_OUTPUT: "AO",
        SignalType.DIGITAL_INPUT: "DI",
        SignalType.DIGITAL_OUTPUT: "DO",
        SignalType.THERMOCOUPLE: "AI",
        SignalType.RTD_3WIRE: "AI",
        SignalType.RTD_4WIRE: "AI",
    }
    return mapping.get(signal_type, "AI")


def group_instruments_by_jb_type(
    instruments: List[Instrument]
) -> dict:
    """
    Group instruments by their appropriate JB type.

    This is useful when planning JB assignments. Analog and digital
    instruments should generally be assigned to separate JBs.

    Args:
        instruments: List of instruments to group

    Returns:
        Dictionary with 'analog' and 'digital' lists of instruments
    """
    groups = {
        "analog": [],
        "digital": []
    }

    for instrument in instruments:
        if instrument.is_analog:
            groups["analog"].append(instrument)
        else:
            groups["digital"].append(instrument)

    return groups


def suggest_jb_count(instruments: List[Instrument], max_per_jb: int = 20) -> dict:
    """
    Suggest the number of JBs needed for a group of instruments.

    Args:
        instruments: List of instruments
        max_per_jb: Maximum instruments per JB

    Returns:
        Dictionary with suggested JB counts by type
    """
    import math

    groups = group_instruments_by_jb_type(instruments)

    analog_count = len(groups["analog"])
    digital_count = len(groups["digital"])

    # Account for 20% spare capacity
    analog_jbs = math.ceil(analog_count / (max_per_jb * 0.8)) if analog_count > 0 else 0
    digital_jbs = math.ceil(digital_count / (max_per_jb * 0.8)) if digital_count > 0 else 0

    return {
        "analog_jbs": analog_jbs,
        "digital_jbs": digital_jbs,
        "total_jbs": analog_jbs + digital_jbs,
        "analog_instruments": analog_count,
        "digital_instruments": digital_count,
    }
