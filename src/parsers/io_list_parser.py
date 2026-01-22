"""Excel I/O list parser for DCS interconnection diagram generator."""

import pandas as pd
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from ..models import Instrument
from .validators import (
    validate_io_list_columns,
    validate_io_list_row,
    ValidationResult,
    ValidationError,
    REQUIRED_COLUMNS,
)


class IOListParseError(Exception):
    """Exception raised for I/O list parsing errors."""
    pass


@dataclass
class ParseResult:
    """Result of parsing an I/O list."""
    instruments: List[Instrument]
    validation_result: ValidationResult
    raw_data: pd.DataFrame
    column_mapping: Dict[str, str]

    @property
    def is_valid(self) -> bool:
        return self.validation_result.is_valid

    @property
    def instrument_count(self) -> int:
        return len(self.instruments)


class IOListParser:
    """Parser for Excel I/O lists."""

    # Common column name variations
    COLUMN_ALIASES = {
        "Tag Number": ["tag number", "tag_number", "tag", "instrument tag", "tag no", "tag no."],
        "Instrument Type": ["instrument type", "inst type", "type", "instrument_type", "instr type"],
        "Service Description": ["service description", "service", "description", "service desc", "service_description"],
        "Area": ["area", "plant area", "area code", "location"],
        "Signal Type": ["signal type", "signal", "signal_type"],
        "Loop Number": ["loop number", "loop", "loop no", "loop_number"],
        "P&ID Reference": ["p&id reference", "p&id", "pid", "p&id ref", "pid_reference"],
        "IO Type": ["io type", "i/o type", "io_type", "i/o"],
        "Cabinet": ["cabinet", "cab", "marshalling cabinet"],
        "JB": ["jb", "junction box", "jb tag"],
        "Remarks": ["remarks", "notes", "comment", "comments"],
    }

    def __init__(self, file_path: str):
        """
        Initialize the parser with a file path.

        Args:
            file_path: Path to the Excel I/O list file
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise IOListParseError(f"File not found: {file_path}")
        if not self.file_path.suffix.lower() in ['.xlsx', '.xls']:
            raise IOListParseError(f"Invalid file type: {self.file_path.suffix}. Expected .xlsx or .xls")

    def _normalize_column_name(self, column: str) -> str:
        """Normalize a column name to standard format."""
        col_lower = str(column).strip().lower()

        for standard_name, aliases in self.COLUMN_ALIASES.items():
            if col_lower == standard_name.lower() or col_lower in aliases:
                return standard_name

        return column

    def _create_column_mapping(self, columns: List[str]) -> Dict[str, str]:
        """Create a mapping from original column names to standard names."""
        mapping = {}
        for col in columns:
            normalized = self._normalize_column_name(col)
            if normalized != col:
                mapping[col] = normalized
        return mapping

    def parse(self, sheet_name: Optional[str] = None) -> ParseResult:
        """
        Parse the I/O list Excel file.

        Args:
            sheet_name: Optional sheet name to parse. If None, uses the first sheet.

        Returns:
            ParseResult with instruments and validation results
        """
        try:
            # Read Excel file
            if sheet_name:
                df = pd.read_excel(self.file_path, sheet_name=sheet_name)
            else:
                df = pd.read_excel(self.file_path)

            # Create column mapping
            column_mapping = self._create_column_mapping(df.columns.tolist())

            # Rename columns to standard names
            if column_mapping:
                df = df.rename(columns=column_mapping)

            # Validate columns
            validation_result = validate_io_list_columns(df.columns.tolist())
            if not validation_result.is_valid:
                return ParseResult(
                    instruments=[],
                    validation_result=validation_result,
                    raw_data=df,
                    column_mapping=column_mapping
                )

            # Parse rows and validate
            instruments = []
            for idx, row in df.iterrows():
                row_dict = row.to_dict()

                # Skip empty rows
                if pd.isna(row_dict.get("Tag Number")) or not str(row_dict.get("Tag Number")).strip():
                    continue

                # Validate row
                row_validation = validate_io_list_row(row_dict, idx + 2)  # +2 for header and 0-index
                validation_result.errors.extend(row_validation.errors)
                validation_result.warnings.extend(row_validation.warnings)

                if row_validation.is_valid:
                    # Create instrument
                    instrument = self._create_instrument(row_dict)
                    instruments.append(instrument)

            # Update validation status
            if validation_result.errors:
                validation_result.is_valid = False

            return ParseResult(
                instruments=instruments,
                validation_result=validation_result,
                raw_data=df,
                column_mapping=column_mapping
            )

        except Exception as e:
            raise IOListParseError(f"Failed to parse I/O list: {str(e)}")

    def _create_instrument(self, row: Dict[str, Any]) -> Instrument:
        """Create an Instrument from a row dictionary."""
        return Instrument(
            tag_number=str(row.get("Tag Number", "")).strip(),
            instrument_type=str(row.get("Instrument Type", "")).strip(),
            service=str(row.get("Service Description", "")).strip(),
            area=str(row.get("Area", "")).strip(),
            loop_number=str(row.get("Loop Number", "")).strip() if pd.notna(row.get("Loop Number")) else None,
            pid_reference=str(row.get("P&ID Reference", "")).strip() if pd.notna(row.get("P&ID Reference")) else None,
            io_type=str(row.get("IO Type", "")).strip() if pd.notna(row.get("IO Type")) else None,
            remarks=str(row.get("Remarks", "")).strip() if pd.notna(row.get("Remarks")) else None,
        )

    def get_sheet_names(self) -> List[str]:
        """Get list of sheet names in the Excel file."""
        xl = pd.ExcelFile(self.file_path)
        return xl.sheet_names


def load_io_list(file_path: str, sheet_name: Optional[str] = None) -> ParseResult:
    """
    Convenience function to load and parse an I/O list.

    Args:
        file_path: Path to the Excel file
        sheet_name: Optional sheet name

    Returns:
        ParseResult with instruments and validation results
    """
    parser = IOListParser(file_path)
    return parser.parse(sheet_name)


def filter_instruments_by_area(
    instruments: List[Instrument],
    area: str
) -> List[Instrument]:
    """Filter instruments by area code."""
    return [i for i in instruments if i.area == str(area)]


def filter_instruments_by_type(
    instruments: List[Instrument],
    is_analog: Optional[bool] = None,
    is_digital: Optional[bool] = None
) -> List[Instrument]:
    """Filter instruments by signal type (analog/digital)."""
    result = instruments

    if is_analog is not None:
        result = [i for i in result if i.is_analog == is_analog]

    if is_digital is not None:
        result = [i for i in result if i.is_digital == is_digital]

    return result


def group_instruments_by_area(
    instruments: List[Instrument]
) -> Dict[str, List[Instrument]]:
    """Group instruments by area code."""
    groups: Dict[str, List[Instrument]] = {}

    for instrument in instruments:
        area = instrument.area
        if area not in groups:
            groups[area] = []
        groups[area].append(instrument)

    return groups


def group_instruments_by_signal_type(
    instruments: List[Instrument]
) -> Dict[str, List[Instrument]]:
    """Group instruments by signal type (ANALOG/DIGITAL)."""
    groups = {
        "ANALOG": [],
        "DIGITAL": []
    }

    for instrument in instruments:
        if instrument.is_analog:
            groups["ANALOG"].append(instrument)
        else:
            groups["DIGITAL"].append(instrument)

    return groups
