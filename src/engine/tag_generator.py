"""Tag number generator for DCS interconnection diagram generator."""

from typing import Optional
from dataclasses import dataclass

from .classifier import JBType, get_jb_tag_prefix


@dataclass
class TagConfig:
    """Configuration for tag generation."""
    plant_code: str = "PP01"
    area_code: str = "601"
    jb_sequence_start: int = 1
    cable_sequence_start: int = 1
    tb_sequence_start: int = 1


class TagGenerator:
    """Generator for various tag numbers."""

    def __init__(self, config: Optional[TagConfig] = None):
        """
        Initialize the tag generator.

        Args:
            config: Optional TagConfig, defaults to standard values
        """
        self.config = config or TagConfig()
        self._jb_counter = {
            JBType.ANALOG: self.config.jb_sequence_start,
            JBType.DIGITAL: self.config.jb_sequence_start,
            JBType.MIXED: self.config.jb_sequence_start,
        }
        self._cable_counter = self.config.cable_sequence_start
        self._tb_counter = self.config.tb_sequence_start

    def generate_jb_tag(self, jb_type: JBType) -> str:
        """
        Generate a junction box tag.

        Format: PP01-601-IAJB00XX (Analog) or PP01-601-IDJB00XX (Digital)

        Args:
            jb_type: JBType enum value

        Returns:
            Generated JB tag
        """
        prefix = get_jb_tag_prefix(jb_type)
        seq = self._jb_counter[jb_type]
        self._jb_counter[jb_type] += 1

        return f"{self.config.plant_code}-{self.config.area_code}-{prefix}JB{seq:04d}"

    def generate_multipair_cable_tag(self) -> str:
        """
        Generate a multipair cable tag.

        Format: PP01-601-I00XX

        Returns:
            Generated cable tag
        """
        seq = self._cable_counter
        self._cable_counter += 1

        return f"{self.config.plant_code}-{self.config.area_code}-I{seq:04d}"

    def generate_terminal_block_tag(self, cable_tag: Optional[str] = None) -> str:
        """
        Generate a terminal block tag.

        Format: TB601-I00XX (matches the multipair cable number)

        Args:
            cable_tag: Optional cable tag to derive TB tag from

        Returns:
            Generated TB tag
        """
        if cable_tag:
            # Extract cable number from tag (e.g., PP01-601-I0004 -> 0004)
            parts = cable_tag.split("-")
            if len(parts) >= 3:
                cable_num = parts[2]  # I0004
                return f"TB{self.config.area_code}-{cable_num}"

        seq = self._tb_counter
        self._tb_counter += 1

        return f"TB{self.config.area_code}-I{seq:04d}"

    def generate_drawing_number(
        self,
        contract: str = "100478",
        discipline: str = "IC",
        doc_type: str = "DIC",
        sequence: int = 1
    ) -> str:
        """
        Generate a drawing number.

        Format: 100478CP-N-PG-PP01-IC-DIC-0004-001

        Args:
            contract: Contract number
            discipline: Discipline code (IC for instrumentation)
            doc_type: Document type (DIC for diagram)
            sequence: Sequence number

        Returns:
            Generated drawing number
        """
        return (
            f"{contract}CP-N-PG-{self.config.plant_code}-"
            f"{discipline}-{doc_type}-{sequence:04d}"
        )

    def reset_counters(self):
        """Reset all sequence counters to starting values."""
        for jb_type in JBType:
            self._jb_counter[jb_type] = self.config.jb_sequence_start
        self._cable_counter = self.config.cable_sequence_start
        self._tb_counter = self.config.tb_sequence_start


def generate_jb_tag(
    plant_code: str,
    area_code: str,
    jb_type: JBType,
    sequence: int
) -> str:
    """
    Generate a junction box tag.

    Args:
        plant_code: Plant/unit code (e.g., "PP01")
        area_code: Area code (e.g., "601")
        jb_type: JBType enum value
        sequence: Sequence number

    Returns:
        Generated JB tag
    """
    prefix = get_jb_tag_prefix(jb_type)
    return f"{plant_code}-{area_code}-{prefix}JB{sequence:04d}"


def generate_multipair_cable_tag(
    plant_code: str,
    area_code: str,
    sequence: int
) -> str:
    """
    Generate a multipair cable tag.

    Args:
        plant_code: Plant/unit code
        area_code: Area code
        sequence: Sequence number

    Returns:
        Generated cable tag
    """
    return f"{plant_code}-{area_code}-I{sequence:04d}"


def generate_tb_tag(area_code: str, cable_sequence: int) -> str:
    """
    Generate a terminal block tag.

    Args:
        area_code: Area code
        cable_sequence: Associated cable sequence number

    Returns:
        Generated TB tag
    """
    return f"TB{area_code}-I{cable_sequence:04d}"


def parse_instrument_tag(tag: str) -> dict:
    """
    Parse an instrument tag into components.

    Args:
        tag: Instrument tag (e.g., "PP01-364-TIT0001")

    Returns:
        Dictionary with parsed components
    """
    import re

    result = {"raw": tag}

    parts = tag.split("-")
    if len(parts) != 3:
        return result

    result["plant_code"] = parts[0]
    result["area_code"] = parts[1]

    # Parse instrument type and sequence
    type_seq = parts[2]
    match = re.match(r'^([A-Z]+)(\d+)$', type_seq)
    if match:
        result["instrument_type"] = match.group(1)
        result["sequence"] = match.group(2)
    else:
        result["type_sequence"] = type_seq

    return result


def parse_jb_tag(tag: str) -> dict:
    """
    Parse a JB tag into components.

    Args:
        tag: JB tag (e.g., "PP01-601-IAJB0002")

    Returns:
        Dictionary with parsed components
    """
    result = {"raw": tag}

    parts = tag.split("-")
    if len(parts) != 3:
        return result

    result["plant_code"] = parts[0]
    result["area_code"] = parts[1]

    # Parse JB type and sequence
    jb_part = parts[2]
    if jb_part.startswith("IA"):
        result["jb_type"] = "ANALOG"
        result["sequence"] = jb_part[4:]  # After "IAJB"
    elif jb_part.startswith("ID"):
        result["jb_type"] = "DIGITAL"
        result["sequence"] = jb_part[4:]
    elif jb_part.startswith("IM"):
        result["jb_type"] = "MIXED"
        result["sequence"] = jb_part[4:]
    else:
        result["jb_part"] = jb_part

    return result
