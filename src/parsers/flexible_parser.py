"""Flexible I/O list parser that handles multiple Excel formats.

This parser can auto-detect and handle:
1. Traditional row-based I/O lists (Tag Number, Instrument Type, Service, Area columns)
2. Column-based I/O summaries (AI, DI, DO, AO columns with tags in rows)
3. Mixed formats with various column naming conventions
"""

import re
import pandas as pd
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from ..models import Instrument


class IOListFormat(Enum):
    """Detected I/O list format types."""
    TRADITIONAL_ROWS = "traditional_rows"      # Standard row-based format
    COLUMN_BY_IO_TYPE = "column_by_io_type"    # Tags organized by I/O type columns
    SINGLE_TAG_COLUMN = "single_tag_column"    # Just a list of tags
    UNKNOWN = "unknown"


@dataclass
class FormatDetectionResult:
    """Result of format detection."""
    format_type: IOListFormat
    confidence: float
    sheet_name: str
    header_row: int
    data_start_row: int
    column_mapping: Dict[str, str]
    notes: List[str]


@dataclass
class FlexibleParseResult:
    """Result of flexible parsing."""
    instruments: List[Instrument]
    format_detected: IOListFormat
    source_sheet: str
    warnings: List[str]
    io_counts: Dict[str, int]
    system_type: Optional[str] = None  # DCS, RTU, SIS/ESD detected from file

    @property
    def is_valid(self) -> bool:
        return len(self.instruments) > 0

    @property
    def instrument_count(self) -> int:
        return len(self.instruments)


# Tag patterns for different naming conventions
TAG_PATTERNS = [
    # Standard: PP01-364-TIT0001
    re.compile(r'^[A-Z]{2}\d{2}-\d{3}-([A-Z]{2,4})\d{4}$'),
    # Simple: 402-PIT-201
    re.compile(r'^(\d{3})-([A-Z]{2,4})-(\d{2,4}[A-Z]?)$'),
    # With letters: 402-RZSO-201A
    re.compile(r'^(\d{3})-([A-Z]{2,6})-(\d{2,4}[A-Z]?)$'),
    # Compact: PIT-201
    re.compile(r'^([A-Z]{2,4})-(\d{2,4}[A-Z]?)$'),
    # Underscore format: 402_PIT_201
    re.compile(r'^(\d{3})_([A-Z]{2,4})_(\d{2,4}[A-Z]?)$'),
    # With area prefix: AREA1-PIT-001
    re.compile(r'^([A-Z]+\d*)-([A-Z]{2,4})-(\d{2,4}[A-Z]?)$'),
]

# I/O type column name variations
IO_TYPE_COLUMN_ALIASES = {
    'AI': ['ai', 'analog input', 'analog_input', 'number of ai', 'ai tags', 'ai count', 'ai signals'],
    'AO': ['ao', 'analog output', 'analog_output', 'number of ao', 'ao tags', 'ao count', 'ao signals'],
    'DI': ['di', 'digital input', 'digital_input', 'number of di', 'di tags', 'di count', 'di signals'],
    'DO': ['do', 'digital output', 'digital_output', 'number of do', 'do tags', 'do count', 'do signals'],
}

# Instrument type to I/O type mapping (commonly used prefixes)
INSTRUMENT_TYPE_IO_MAPPING = {
    # Analog Inputs
    'PIT': 'AI', 'TIT': 'AI', 'FIT': 'AI', 'LIT': 'AI', 'AIT': 'AI',
    'PDT': 'AI', 'WIT': 'AI', 'VIT': 'AI', 'SIT': 'AI', 'TE': 'AI',
    'PT': 'AI', 'TT': 'AI', 'FT': 'AI', 'LT': 'AI', 'AT': 'AI',
    'ET': 'AI', 'IT': 'AI',  # Common transmitter types

    # Analog Outputs
    'TY': 'AO', 'PY': 'AO', 'FY': 'AO', 'LY': 'AO',
    'TV': 'AO', 'PV': 'AO', 'FV': 'AO', 'LV': 'AO',  # Control valves

    # Digital Inputs
    'ZS': 'DI', 'ZSC': 'DI', 'ZSO': 'DI', 'RZSO': 'DI', 'RZSC': 'DI',
    'MZSO': 'DI', 'MZSC': 'DI', 'EZSO': 'DI', 'EZSC': 'DI',
    'BZSO': 'DI', 'BZSC': 'DI',
    'PSL': 'DI', 'PSH': 'DI', 'PSLL': 'DI', 'PSHH': 'DI',
    'LSL': 'DI', 'LSH': 'DI', 'LSLL': 'DI', 'LSHH': 'DI',
    'TSL': 'DI', 'TSH': 'DI', 'TSLL': 'DI', 'TSHH': 'DI',
    'FS': 'DI', 'FSL': 'DI', 'FSH': 'DI',
    'XS': 'DI', 'MXS': 'DI',  # General switches

    # Digital Outputs
    'XV': 'DO', 'XY': 'DO', 'SOV': 'DO', 'SV': 'DO',
    'RSOV': 'DO', 'MOV': 'DO',  # Valves/solenoids
}


def extract_instrument_type_from_tag(tag: str) -> Tuple[str, str]:
    """
    Extract instrument type from a tag number.

    Returns:
        Tuple of (instrument_type, area_code)
    """
    if not tag or not isinstance(tag, str):
        return '', ''

    tag = tag.strip().upper()

    for pattern in TAG_PATTERNS:
        match = pattern.match(tag)
        if match:
            groups = match.groups()
            if len(groups) >= 2:
                # For patterns like 402-PIT-201, groups are (area, type, seq)
                if len(groups) == 3 and groups[0].isdigit():
                    return groups[1], groups[0]
                # For patterns like PP01-364-TIT0001, type is in position 0
                elif len(groups) == 1:
                    return groups[0], ''

    # Fallback: try to find instrument type in the tag
    parts = re.split(r'[-_]', tag)
    for part in parts:
        # Check if this part looks like an instrument type
        if re.match(r'^[A-Z]{2,6}$', part) and part in INSTRUMENT_TYPE_IO_MAPPING:
            return part, ''
        # Extract letters from alphanumeric parts
        letters = re.sub(r'[^A-Z]', '', part)
        if letters and letters in INSTRUMENT_TYPE_IO_MAPPING:
            return letters, ''

    return '', ''


def extract_area_from_tag(tag: str) -> str:
    """Extract area code from a tag number."""
    if not tag or not isinstance(tag, str):
        return ''

    tag = tag.strip().upper()

    # Try to find 3-digit area code
    match = re.search(r'(\d{3})', tag)
    if match:
        return match.group(1)

    # Try to find any numeric prefix
    parts = re.split(r'[-_]', tag)
    for part in parts:
        if part.isdigit():
            return part

    return ''


def infer_io_type_from_instrument_type(inst_type: str) -> str:
    """Infer I/O type from instrument type."""
    if not inst_type:
        return ''

    inst_type = inst_type.strip().upper()

    # Direct lookup
    if inst_type in INSTRUMENT_TYPE_IO_MAPPING:
        return INSTRUMENT_TYPE_IO_MAPPING[inst_type]

    # Try prefix matching for longer types
    for prefix in sorted(INSTRUMENT_TYPE_IO_MAPPING.keys(), key=len, reverse=True):
        if inst_type.startswith(prefix):
            return INSTRUMENT_TYPE_IO_MAPPING[prefix]

    return ''


def is_valid_tag(value: Any) -> bool:
    """Check if a value looks like a valid instrument tag."""
    if pd.isna(value):
        return False

    val_str = str(value).strip()
    if not val_str or val_str.lower() in ['nan', 'none', '', 'spare', 'reserved']:
        return False

    # Must contain at least one letter and one digit
    has_letter = any(c.isalpha() for c in val_str)
    has_digit = any(c.isdigit() for c in val_str)

    # Must not be too short or too long
    if len(val_str) < 4 or len(val_str) > 30:
        return False

    return has_letter and has_digit


class FlexibleIOListParser:
    """Flexible parser that handles multiple I/O list formats."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        self.xl_file = pd.ExcelFile(file_path)
        self.warnings: List[str] = []

    def get_sheet_names(self) -> List[str]:
        """Get list of sheet names."""
        return self.xl_file.sheet_names

    def detect_format(self, df: pd.DataFrame, sheet_name: str) -> FormatDetectionResult:
        """Detect the format of an I/O list DataFrame."""
        notes = []
        columns_lower = [str(c).strip().lower() for c in df.columns]

        # Check for traditional row-based format
        traditional_score = 0
        column_mapping = {}

        traditional_aliases = {
            'tag number': ['tag number', 'tag_number', 'tag', 'instrument tag', 'tag no', 'tag no.'],
            'instrument type': ['instrument type', 'inst type', 'type', 'instrument_type'],
            'service': ['service', 'service description', 'description'],
            'area': ['area', 'plant area', 'area code', 'location'],
            'io type': ['io type', 'i/o type', 'io_type', 'signal type'],
        }

        for std_name, aliases in traditional_aliases.items():
            for alias in aliases:
                if alias in columns_lower:
                    traditional_score += 1
                    idx = columns_lower.index(alias)
                    column_mapping[df.columns[idx]] = std_name.title().replace('_', ' ')
                    break

        # Check for column-by-io-type format (tags in AI, DI, DO, AO columns)
        io_type_score = 0
        io_type_columns = {}

        for io_type, aliases in IO_TYPE_COLUMN_ALIASES.items():
            for alias in aliases:
                if alias in columns_lower:
                    io_type_score += 1
                    idx = columns_lower.index(alias)
                    io_type_columns[io_type] = df.columns[idx]
                    break

        # Also check raw header values for IO type patterns
        for idx, col in enumerate(df.columns):
            col_str = str(col).strip().lower()
            for io_type, aliases in IO_TYPE_COLUMN_ALIASES.items():
                if io_type not in io_type_columns:
                    if any(alias in col_str for alias in aliases):
                        io_type_score += 1
                        io_type_columns[io_type] = col
                        break

        # Determine format based on scores
        if io_type_score >= 2:
            notes.append(f"Detected IO type columns: {list(io_type_columns.keys())}")
            return FormatDetectionResult(
                format_type=IOListFormat.COLUMN_BY_IO_TYPE,
                confidence=min(io_type_score / 4.0, 1.0),
                sheet_name=sheet_name,
                header_row=0,
                data_start_row=1,
                column_mapping=io_type_columns,
                notes=notes
            )
        elif traditional_score >= 2:
            notes.append(f"Detected traditional columns: {list(column_mapping.values())}")
            return FormatDetectionResult(
                format_type=IOListFormat.TRADITIONAL_ROWS,
                confidence=min(traditional_score / 4.0, 1.0),
                sheet_name=sheet_name,
                header_row=0,
                data_start_row=1,
                column_mapping=column_mapping,
                notes=notes
            )

        # Try to detect by scanning cell contents
        return self._detect_by_content_analysis(df, sheet_name)

    def _detect_by_content_analysis(self, df: pd.DataFrame, sheet_name: str) -> FormatDetectionResult:
        """Detect format by analyzing cell contents."""
        notes = []

        # Scan first 20 rows to find header row
        for row_idx in range(min(20, len(df))):
            row_values = [str(v).strip().lower() for v in df.iloc[row_idx].values if pd.notna(v)]

            # Check for IO type headers in this row
            io_types_found = {}
            for col_idx, val in enumerate(df.iloc[row_idx].values):
                if pd.isna(val):
                    continue
                val_lower = str(val).strip().lower()
                for io_type, aliases in IO_TYPE_COLUMN_ALIASES.items():
                    if any(alias in val_lower for alias in aliases):
                        io_types_found[io_type] = df.columns[col_idx]

            if len(io_types_found) >= 2:
                notes.append(f"Found IO type headers at row {row_idx}: {list(io_types_found.keys())}")
                return FormatDetectionResult(
                    format_type=IOListFormat.COLUMN_BY_IO_TYPE,
                    confidence=0.8,
                    sheet_name=sheet_name,
                    header_row=row_idx,
                    data_start_row=row_idx + 1,
                    column_mapping=io_types_found,
                    notes=notes
                )

        # Check for single column of tags
        for col in df.columns:
            valid_tags = df[col].apply(is_valid_tag).sum()
            if valid_tags > 5:  # At least 5 valid-looking tags
                notes.append(f"Found tag column: {col} with {valid_tags} tags")
                return FormatDetectionResult(
                    format_type=IOListFormat.SINGLE_TAG_COLUMN,
                    confidence=0.6,
                    sheet_name=sheet_name,
                    header_row=0,
                    data_start_row=0,
                    column_mapping={'tags': col},
                    notes=notes
                )

        notes.append("Could not determine format with confidence")
        return FormatDetectionResult(
            format_type=IOListFormat.UNKNOWN,
            confidence=0.0,
            sheet_name=sheet_name,
            header_row=0,
            data_start_row=0,
            column_mapping={},
            notes=notes
        )

    def _parse_column_by_io_type(self, df: pd.DataFrame, detection: FormatDetectionResult) -> List[Instrument]:
        """Parse a column-by-IO-type format (AI, DI, DO, AO columns)."""
        instruments = []

        # Re-read with correct header row
        if detection.header_row > 0:
            df = pd.read_excel(self.file_path, sheet_name=detection.sheet_name,
                              header=detection.header_row)

        # For each IO type column, extract tags
        for io_type_from_column, col_name in detection.column_mapping.items():
            if col_name not in df.columns:
                # Try to find column by searching all columns
                for col in df.columns:
                    col_lower = str(col).strip().lower()
                    if any(alias in col_lower for alias in IO_TYPE_COLUMN_ALIASES.get(io_type_from_column, [])):
                        col_name = col
                        break

            if col_name not in df.columns:
                self.warnings.append(f"Column for {io_type_from_column} not found: {col_name}")
                continue

            for idx, value in df[col_name].items():
                if not is_valid_tag(value):
                    continue

                tag = str(value).strip().upper()
                inst_type, area = extract_instrument_type_from_tag(tag)

                # If we couldn't extract instrument type, try to infer from tag patterns
                if not inst_type:
                    parts = re.split(r'[-_]', tag)
                    for part in parts:
                        letters = re.sub(r'[^A-Z]', '', part.upper())
                        if letters and len(letters) >= 2:
                            inst_type = letters
                            break
                    if not inst_type:
                        inst_type = io_type_from_column  # Fallback to column IO type

                if not area:
                    area = extract_area_from_tag(tag)

                # Determine the actual IO type based on instrument type
                # This is more reliable than the column header
                actual_io_type = infer_io_type_from_instrument_type(inst_type)

                # If we can't infer IO type from instrument type, use the column header
                if not actual_io_type:
                    actual_io_type = io_type_from_column

                instruments.append(Instrument(
                    tag_number=tag,
                    instrument_type=inst_type,
                    service=f"{actual_io_type} Signal",
                    area=area or "000",
                    io_type=actual_io_type,
                ))

        return instruments

    def _parse_traditional_rows(self, df: pd.DataFrame, detection: FormatDetectionResult) -> List[Instrument]:
        """Parse traditional row-based format."""
        instruments = []

        # Apply column mapping
        if detection.column_mapping:
            df = df.rename(columns=detection.column_mapping)

        # Normalize column names
        col_map = {}
        for col in df.columns:
            col_lower = str(col).strip().lower()
            if 'tag' in col_lower and 'number' in col_lower or col_lower == 'tag':
                col_map[col] = 'Tag Number'
            elif 'instrument' in col_lower and 'type' in col_lower or col_lower == 'type':
                col_map[col] = 'Instrument Type'
            elif 'service' in col_lower or 'description' in col_lower:
                col_map[col] = 'Service'
            elif col_lower == 'area' or 'area' in col_lower:
                col_map[col] = 'Area'
            elif 'io' in col_lower and 'type' in col_lower:
                col_map[col] = 'IO Type'

        if col_map:
            df = df.rename(columns=col_map)

        for idx, row in df.iterrows():
            tag = row.get('Tag Number', '')
            if not is_valid_tag(tag):
                continue

            tag = str(tag).strip().upper()
            inst_type = str(row.get('Instrument Type', '')).strip().upper()

            # Try to extract instrument type from tag if not provided
            if not inst_type or inst_type.lower() in ['nan', 'none', '']:
                inst_type, _ = extract_instrument_type_from_tag(tag)

            area = str(row.get('Area', '')).strip()
            if not area or area.lower() in ['nan', 'none', '']:
                area = extract_area_from_tag(tag)

            service = str(row.get('Service', '')).strip()
            if service.lower() in ['nan', 'none', '']:
                service = ''

            io_type = str(row.get('IO Type', '')).strip().upper()
            if io_type.lower() in ['nan', 'none', '']:
                io_type = infer_io_type_from_instrument_type(inst_type)

            instruments.append(Instrument(
                tag_number=tag,
                instrument_type=inst_type or 'UNKNOWN',
                service=service or f"{io_type} Signal" if io_type else "Instrument",
                area=area or "000",
                io_type=io_type if io_type else None,
            ))

        return instruments

    def _parse_single_tag_column(self, df: pd.DataFrame, detection: FormatDetectionResult) -> List[Instrument]:
        """Parse a single column of tags."""
        instruments = []
        tag_col = detection.column_mapping.get('tags')

        if tag_col not in df.columns:
            return instruments

        for idx, value in df[tag_col].items():
            if not is_valid_tag(value):
                continue

            tag = str(value).strip().upper()
            inst_type, area = extract_instrument_type_from_tag(tag)
            io_type = infer_io_type_from_instrument_type(inst_type)

            instruments.append(Instrument(
                tag_number=tag,
                instrument_type=inst_type or 'UNKNOWN',
                service=f"{io_type} Signal" if io_type else "Instrument",
                area=area or extract_area_from_tag(tag) or "000",
                io_type=io_type if io_type else None,
            ))

        return instruments

    def parse(self, sheet_name: Optional[str] = None) -> FlexibleParseResult:
        """
        Parse the I/O list with automatic format detection.

        Args:
            sheet_name: Optional specific sheet to parse. If None, will try all sheets.

        Returns:
            FlexibleParseResult with instruments and metadata
        """
        self.warnings = []
        all_instruments = []
        best_detection = None
        best_sheet = None

        sheets_to_try = [sheet_name] if sheet_name else self.xl_file.sheet_names

        for sheet in sheets_to_try:
            try:
                # Read with no header first for analysis
                df_raw = pd.read_excel(self.file_path, sheet_name=sheet, header=None)

                # Try to find the actual header row
                header_row = self._find_header_row(df_raw)

                # Re-read with detected header
                if header_row > 0:
                    df = pd.read_excel(self.file_path, sheet_name=sheet, header=header_row)
                else:
                    df = pd.read_excel(self.file_path, sheet_name=sheet)

                detection = self.detect_format(df, sheet)

                if detection.format_type == IOListFormat.UNKNOWN:
                    self.warnings.append(f"Sheet '{sheet}': Could not detect format")
                    continue

                # Parse based on detected format
                if detection.format_type == IOListFormat.COLUMN_BY_IO_TYPE:
                    instruments = self._parse_column_by_io_type(df, detection)
                elif detection.format_type == IOListFormat.TRADITIONAL_ROWS:
                    instruments = self._parse_traditional_rows(df, detection)
                elif detection.format_type == IOListFormat.SINGLE_TAG_COLUMN:
                    instruments = self._parse_single_tag_column(df, detection)
                else:
                    instruments = []

                if instruments:
                    if best_detection is None or len(instruments) > len(all_instruments):
                        all_instruments = instruments
                        best_detection = detection
                        best_sheet = sheet
                    self.warnings.append(f"Sheet '{sheet}': Found {len(instruments)} instruments ({detection.format_type.value})")

            except Exception as e:
                self.warnings.append(f"Sheet '{sheet}': Error - {str(e)}")

        # Calculate I/O counts
        io_counts = {'AI': 0, 'AO': 0, 'DI': 0, 'DO': 0}
        for inst in all_instruments:
            if inst.io_type in io_counts:
                io_counts[inst.io_type] += 1
            else:
                # Infer from instrument type
                inferred = infer_io_type_from_instrument_type(inst.instrument_type)
                if inferred in io_counts:
                    io_counts[inferred] += 1

        # Detect system type from the best sheet
        system_type = None
        if best_sheet:
            try:
                df_for_detection = pd.read_excel(self.file_path, sheet_name=best_sheet, header=None)
                system_type = self._detect_system_type(df_for_detection)
            except Exception:
                pass

        return FlexibleParseResult(
            instruments=all_instruments,
            format_detected=best_detection.format_type if best_detection else IOListFormat.UNKNOWN,
            source_sheet=best_sheet or "",
            warnings=self.warnings,
            io_counts=io_counts,
            system_type=system_type
        )

    def _find_header_row(self, df: pd.DataFrame) -> int:
        """Find the likely header row in a DataFrame."""
        # Look for rows that contain IO type keywords or standard column names
        keywords = ['ai', 'di', 'do', 'ao', 'tag', 'number', 'type', 'service', 'area',
                   'analog', 'digital', 'input', 'output', 'instrument']

        for row_idx in range(min(10, len(df))):
            row_values = [str(v).strip().lower() for v in df.iloc[row_idx].values if pd.notna(v)]
            row_text = ' '.join(row_values)

            matches = sum(1 for kw in keywords if kw in row_text)
            if matches >= 2:
                return row_idx

        return 0

    def _detect_system_type(self, df: pd.DataFrame) -> Optional[str]:
        """
        Detect system type (RTU, DCS, SIS/ESD) from file content.

        Looks for keywords in:
        - Sheet name
        - First few rows (title, header areas)
        - Column headers

        Returns:
            System type string: 'RTU', 'DCS', 'SIS', 'ESD', or None
        """
        # Check first 5 rows for system type keywords
        system_keywords = {
            'RTU': ['rtu', 'remote terminal unit', 'rtu i/o', 'rtu io'],
            'DCS': ['dcs', 'distributed control', 'dcs i/o', 'dcs io'],
            'SIS': ['sis', 'safety instrumented', 'sis i/o', 'sis io'],
            'ESD': ['esd', 'emergency shutdown', 'esd i/o', 'esd io'],
        }

        # Collect text from first few rows
        text_to_check = []
        for row_idx in range(min(5, len(df))):
            row_values = [str(v).strip().lower() for v in df.iloc[row_idx].values if pd.notna(v)]
            text_to_check.extend(row_values)

        search_text = ' '.join(text_to_check)

        # Check for each system type
        for system_type, keywords in system_keywords.items():
            if any(keyword in search_text for keyword in keywords):
                self.warnings.append(f"Detected system type: {system_type}")
                return system_type

        return None


def load_io_list_flexible(file_path: str, sheet_name: Optional[str] = None) -> FlexibleParseResult:
    """
    Convenience function to load and parse an I/O list with flexible format detection.

    Args:
        file_path: Path to the Excel file
        sheet_name: Optional specific sheet to parse

    Returns:
        FlexibleParseResult with instruments and metadata
    """
    parser = FlexibleIOListParser(file_path)
    return parser.parse(sheet_name)
