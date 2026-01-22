"""Parsers for DCS interconnection diagram generator."""

from .io_list_parser import (
    IOListParser,
    IOListParseError,
    ParseResult,
    load_io_list as _load_io_list_strict,
    filter_instruments_by_area,
    filter_instruments_by_type,
    group_instruments_by_area,
    group_instruments_by_signal_type,
)

from .validators import (
    ValidationError,
    ValidationResult,
    validate_tag_number,
    validate_instrument_type,
    validate_io_list_columns,
    validate_io_list_row,
    parse_tag_components,
    REQUIRED_COLUMNS,
    OPTIONAL_COLUMNS,
)

from .flexible_parser import (
    FlexibleIOListParser,
    FlexibleParseResult,
    IOListFormat,
    FormatDetectionResult,
    load_io_list_flexible,
    extract_instrument_type_from_tag,
    extract_area_from_tag,
    infer_io_type_from_instrument_type,
)


def load_io_list(file_path: str, sheet_name=None) -> ParseResult:
    """
    Load and parse an I/O list with automatic format detection.

    First tries the strict parser, then falls back to the flexible parser
    if the strict parser fails validation.

    Args:
        file_path: Path to the Excel file
        sheet_name: Optional specific sheet to parse

    Returns:
        ParseResult with instruments and validation results
    """
    # First try the strict parser
    try:
        result = _load_io_list_strict(file_path, sheet_name)
        if result.is_valid and len(result.instruments) > 0:
            return result
    except Exception:
        pass

    # Fall back to flexible parser
    try:
        flex_result = load_io_list_flexible(file_path, sheet_name)

        if flex_result.instruments:
            # Convert FlexibleParseResult to ParseResult for compatibility
            import pandas as pd

            # Create a validation result that passes
            validation = ValidationResult.success()

            # Add warnings from flexible parser
            for warning in flex_result.warnings:
                validation.warnings.append(ValidationError(
                    field="format",
                    message=warning
                ))

            result = ParseResult(
                instruments=flex_result.instruments,
                validation_result=validation,
                raw_data=pd.DataFrame(),  # Empty for flexible parser
                column_mapping={}
            )

            # Attach system_type as an attribute for use by allocator
            result.system_type = flex_result.system_type

            return result
    except Exception as e:
        pass

    # If both fail, return the strict parser result with errors
    return _load_io_list_strict(file_path, sheet_name)

# PDF extractor (optional - may not be available)
try:
    from .pdf_extractor import (
        PDFExtractor,
        ExtractedInstrument,
        ExtractionResult,
        extract_instruments_from_pdf,
        get_pdf_page_as_image,
    )
    PDF_EXTRACTION_AVAILABLE = True
except ImportError:
    PDF_EXTRACTION_AVAILABLE = False

__all__ = [
    # Parser
    "IOListParser",
    "IOListParseError",
    "ParseResult",
    "load_io_list",
    "filter_instruments_by_area",
    "filter_instruments_by_type",
    "group_instruments_by_area",
    "group_instruments_by_signal_type",
    # Flexible Parser
    "FlexibleIOListParser",
    "FlexibleParseResult",
    "IOListFormat",
    "FormatDetectionResult",
    "load_io_list_flexible",
    "extract_instrument_type_from_tag",
    "extract_area_from_tag",
    "infer_io_type_from_instrument_type",
    # Validators
    "ValidationError",
    "ValidationResult",
    "validate_tag_number",
    "validate_instrument_type",
    "validate_io_list_columns",
    "validate_io_list_row",
    "parse_tag_components",
    "REQUIRED_COLUMNS",
    "OPTIONAL_COLUMNS",
    # PDF Extractor
    "PDF_EXTRACTION_AVAILABLE",
]

# Add PDF exports if available
if PDF_EXTRACTION_AVAILABLE:
    __all__.extend([
        "PDFExtractor",
        "ExtractedInstrument",
        "ExtractionResult",
        "extract_instruments_from_pdf",
        "get_pdf_page_as_image",
    ])
