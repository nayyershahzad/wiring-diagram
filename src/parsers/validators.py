"""Input validation utilities for DCS interconnection diagram generator."""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ValidationError:
    """Represents a validation error."""
    field: str
    message: str
    row: Optional[int] = None
    value: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]

    @classmethod
    def success(cls) -> "ValidationResult":
        return cls(is_valid=True, errors=[], warnings=[])

    @classmethod
    def failure(cls, errors: List[ValidationError]) -> "ValidationResult":
        return cls(is_valid=False, errors=errors, warnings=[])

    def add_error(self, error: ValidationError):
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: ValidationError):
        self.warnings.append(warning)


# Tag number pattern: PP01-XXX-YYYNNNN
TAG_PATTERN = re.compile(r'^[A-Z]{2}\d{2}-\d{3}-[A-Z]{2,4}\d{4}$')

# Instrument type pattern
INSTRUMENT_TYPE_PATTERN = re.compile(r'^[A-Z]{2,4}$')


REQUIRED_COLUMNS = [
    "Tag Number",
    "Instrument Type",
    "Service Description",
    "Area",
]

OPTIONAL_COLUMNS = [
    "Signal Type",
    "Loop Number",
    "P&ID Reference",
    "IO Type",
    "Cabinet",
    "JB",
    "Remarks",
]

VALID_IO_TYPES = ["AI", "AO", "DI", "DO"]


def validate_tag_number(tag: str) -> Tuple[bool, str]:
    """
    Validate instrument tag number format.

    Expected format: PP01-XXX-YYYNNNN
    Where:
        - PP01: Plant/Unit code (2 letters + 2 digits)
        - XXX: Area code (3 digits)
        - YYY: Instrument type (2-4 letters)
        - NNNN: Sequential number (4 digits)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not tag:
        return False, "Tag number is empty"

    # More flexible pattern to accommodate variations
    pattern = re.compile(r'^[A-Z]{2}\d{2}-\d{3}-[A-Z]{2,4}\d{4}$')

    if not pattern.match(tag):
        return False, f"Invalid tag format: {tag}. Expected: PP01-XXX-YYYNNNN"

    return True, ""


def validate_instrument_type(inst_type: str) -> Tuple[bool, str]:
    """
    Validate instrument type.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not inst_type:
        return False, "Instrument type is empty"

    if not INSTRUMENT_TYPE_PATTERN.match(inst_type):
        return False, f"Invalid instrument type format: {inst_type}"

    return True, ""


def validate_area(area: str) -> Tuple[bool, str]:
    """
    Validate area code.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not area:
        return False, "Area is empty"

    # Area should be numeric or alphanumeric
    if not str(area).strip():
        return False, "Area is empty"

    return True, ""


def validate_io_list_columns(columns: List[str]) -> ValidationResult:
    """
    Validate that I/O list has required columns.

    Args:
        columns: List of column names from the Excel file

    Returns:
        ValidationResult with errors for missing columns
    """
    result = ValidationResult.success()

    # Normalize column names for comparison
    normalized_columns = [c.strip().lower() for c in columns]

    for required in REQUIRED_COLUMNS:
        normalized_required = required.strip().lower()
        if normalized_required not in normalized_columns:
            result.add_error(ValidationError(
                field=required,
                message=f"Required column missing: {required}"
            ))

    return result


def validate_io_list_row(row: dict, row_number: int) -> ValidationResult:
    """
    Validate a single row from the I/O list.

    Args:
        row: Dictionary of row data
        row_number: Row number for error reporting

    Returns:
        ValidationResult with any errors found
    """
    result = ValidationResult.success()

    # Validate tag number
    tag = row.get("Tag Number", "")
    is_valid, error_msg = validate_tag_number(str(tag))
    if not is_valid:
        result.add_error(ValidationError(
            field="Tag Number",
            message=error_msg,
            row=row_number,
            value=str(tag)
        ))

    # Validate instrument type
    inst_type = row.get("Instrument Type", "")
    is_valid, error_msg = validate_instrument_type(str(inst_type))
    if not is_valid:
        result.add_error(ValidationError(
            field="Instrument Type",
            message=error_msg,
            row=row_number,
            value=str(inst_type)
        ))

    # Validate area
    area = row.get("Area", "")
    is_valid, error_msg = validate_area(str(area))
    if not is_valid:
        result.add_error(ValidationError(
            field="Area",
            message=error_msg,
            row=row_number,
            value=str(area)
        ))

    # Validate IO Type if present
    io_type = row.get("IO Type", "")
    if io_type and str(io_type).upper() not in VALID_IO_TYPES:
        result.add_warning(ValidationError(
            field="IO Type",
            message=f"Unknown IO type: {io_type}. Valid types: {VALID_IO_TYPES}",
            row=row_number,
            value=str(io_type)
        ))

    return result


def parse_tag_components(tag: str) -> dict:
    """
    Parse a tag number into its components.

    Args:
        tag: Tag number string (e.g., "PP01-364-TIT0001")

    Returns:
        Dictionary with parsed components:
        - plant: Plant/unit code (e.g., "PP01")
        - area: Area code (e.g., "364")
        - instrument_type: Instrument type (e.g., "TIT")
        - sequence: Sequence number (e.g., "0001")
    """
    if not tag:
        return {}

    parts = tag.split("-")
    if len(parts) != 3:
        return {"raw": tag}

    plant = parts[0]
    area = parts[1]
    type_seq = parts[2]

    # Split type and sequence
    match = re.match(r'^([A-Z]+)(\d+)$', type_seq)
    if match:
        inst_type = match.group(1)
        sequence = match.group(2)
    else:
        inst_type = type_seq
        sequence = ""

    return {
        "plant": plant,
        "area": area,
        "instrument_type": inst_type,
        "sequence": sequence,
        "raw": tag
    }
