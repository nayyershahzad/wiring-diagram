"""PDF instrument data extractor using OCR and pattern matching."""

import re
import io
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from PIL import Image

try:
    from pdf2image import convert_from_path, convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from ..models import Instrument, SignalType
from ..models.instrument import INSTRUMENT_CLASSIFICATION


@dataclass
class ExtractedInstrument:
    """Represents an instrument extracted from PDF."""
    tag_number: str
    instrument_type: str
    confidence: float
    source_text: str
    area: Optional[str] = None
    service: Optional[str] = None


@dataclass
class ExtractionResult:
    """Result of PDF extraction."""
    instruments: List[ExtractedInstrument]
    raw_text: str
    page_count: int
    warnings: List[str]


# Instrument tag patterns
# Format: PP01-XXX-YYYNNNN or variations
TAG_PATTERNS = [
    # Standard format: PP01-364-TIT0001 (2-6 char instrument type, 3-4 digit number)
    r'([A-Z]{2}\d{2})-(\d{3})-([A-Z]{2,6})(\d{3,4})',
    # Without plant code: 364-TIT0001
    r'(\d{3})-([A-Z]{2,6})(\d{3,4})',
    # Simple format with mandatory 4 digits: TIT0001
    r'([A-Z]{2,6})(\d{4})',
    # Simple format with dash: TIT-0001 or TIT-001
    r'([A-Z]{2,6})-(\d{3,4})',
    # Format with underscore: TIT_0001
    r'([A-Z]{2,6})_(\d{3,4})',
    # With area but no plant: 364TIT0001 (no dash)
    r'(\d{3})([A-Z]{2,6})(\d{3,4})',
]

# Extended instrument types that may have longer prefixes
EXTENDED_INSTRUMENT_TYPES = [
    # Emergency/Bypass position switches
    'EZSC', 'EZSO', 'BZSC', 'BZSO', 'EZLO', 'EZLC', 'EZA',
    # Very high/low switches
    'PSHH', 'PSLL', 'LSLL', 'LSHH', 'TSHH', 'TSLL', 'FSHH', 'FSLL',
    # SIS Indicators
    'TZI', 'PZI', 'FZI', 'LZI', 'TZT', 'PZT', 'FZT', 'LZT',
    # Controllers
    'TIC', 'PIC', 'FIC', 'LIC', 'AIC', 'PDIC',
    # Indicators
    'PDI', 'TAH', 'TAL', 'PAH', 'PAL', 'LAH', 'LAL',
    # Deviation alarms
    'LAD', 'TAD', 'PAD', 'FAD',
    # Equipment status
    'EEHZY', 'MOV', 'SDV', 'SOV',
]

# Backward compatibility alias
EXTENDED_DIGITAL_TYPES = EXTENDED_INSTRUMENT_TYPES

# Common OCR misreads to correct
OCR_CORRECTIONS = {
    '0': 'O',  # Zero misread as O in instrument type
    'O': '0',  # O misread as zero in numbers
    '1': 'I',  # One misread as I
    'I': '1',  # I misread as one in numbers
    'l': '1',  # lowercase L misread as 1
    '5': 'S',  # 5 misread as S
    'S': '5',  # S misread as 5 in numbers
    '8': 'B',  # 8 misread as B
    'B': '8',  # B misread as 8 in numbers
}

# Known instrument type prefixes
INSTRUMENT_TYPES = list(INSTRUMENT_CLASSIFICATION.keys())


class PDFExtractor:
    """Extracts instrument data from PDF documents."""

    def __init__(self, default_plant_code: str = "PP01", default_area: str = "000"):
        """
        Initialize the PDF extractor.

        Args:
            default_plant_code: Default plant code if not found in tags
            default_area: Default area code if not found in tags
        """
        self.default_plant_code = default_plant_code
        self.default_area = default_area

        if not PDF2IMAGE_AVAILABLE:
            raise ImportError("pdf2image is required. Install with: pip install pdf2image")

        if not TESSERACT_AVAILABLE:
            raise ImportError("pytesseract is required. Install with: pip install pytesseract")

    def extract_from_file(
        self,
        pdf_path: str,
        pages: Optional[List[int]] = None,
        dpi: int = 300
    ) -> ExtractionResult:
        """
        Extract instrument data from a PDF file.

        Args:
            pdf_path: Path to the PDF file
            pages: Optional list of page numbers to process (1-indexed)
            dpi: DPI for PDF to image conversion

        Returns:
            ExtractionResult with extracted instruments
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Convert PDF to images
        if pages:
            images = convert_from_path(pdf_path, dpi=dpi, first_page=min(pages), last_page=max(pages))
        else:
            images = convert_from_path(pdf_path, dpi=dpi)

        return self._process_images(images)

    def extract_from_bytes(
        self,
        pdf_bytes: bytes,
        dpi: int = 300
    ) -> ExtractionResult:
        """
        Extract instrument data from PDF bytes.

        Args:
            pdf_bytes: PDF file content as bytes
            dpi: DPI for conversion

        Returns:
            ExtractionResult with extracted instruments
        """
        images = convert_from_bytes(pdf_bytes, dpi=dpi)
        return self._process_images(images)

    def extract_from_region(
        self,
        pdf_path: str,
        page: int,
        region: Tuple[int, int, int, int],
        dpi: int = 300
    ) -> ExtractionResult:
        """
        Extract instrument data from a specific region of a PDF page.

        Args:
            pdf_path: Path to the PDF file
            page: Page number (1-indexed)
            region: Region as (left, top, right, bottom) in pixels
            dpi: DPI for conversion

        Returns:
            ExtractionResult with extracted instruments
        """
        images = convert_from_path(pdf_path, dpi=dpi, first_page=page, last_page=page)

        if not images:
            return ExtractionResult([], "", 0, ["No pages found"])

        # Crop to region
        img = images[0]
        cropped = img.crop(region)

        return self._process_images([cropped])

    def _process_images(self, images: List[Image.Image]) -> ExtractionResult:
        """Process images and extract instrument data."""
        all_text = []
        all_instruments = []
        warnings = []

        for i, img in enumerate(images):
            # Perform OCR with multiple attempts
            try:
                # First attempt: standard OCR
                text = pytesseract.image_to_string(img)
                all_text.append(f"--- Page {i+1} ---\n{text}")

                # Extract instruments from text
                instruments = self._extract_instruments_from_text(text)
                all_instruments.extend(instruments)

                # Second attempt: preprocessed image for better OCR
                preprocessed = self._preprocess_image(img)
                if preprocessed:
                    text2 = pytesseract.image_to_string(preprocessed)
                    if text2 != text:
                        instruments2 = self._extract_instruments_from_text(text2)
                        all_instruments.extend(instruments2)
                        all_text.append(f"--- Page {i+1} (enhanced) ---\n{text2}")

                # Third attempt: OCR with PSM 6 (assume single uniform block of text)
                try:
                    text3 = pytesseract.image_to_string(img, config='--psm 6')
                    if text3 not in [text, text2 if preprocessed else text]:
                        instruments3 = self._extract_instruments_from_text(text3)
                        all_instruments.extend(instruments3)
                except:
                    pass

            except Exception as e:
                warnings.append(f"Error processing page {i+1}: {str(e)}")

        # Remove duplicates
        unique_instruments = self._deduplicate_instruments(all_instruments)

        return ExtractionResult(
            instruments=unique_instruments,
            raw_text="\n\n".join(all_text),
            page_count=len(images),
            warnings=warnings
        )

    def _preprocess_image(self, img: Image.Image) -> Optional[Image.Image]:
        """Preprocess image to improve OCR quality."""
        try:
            import numpy as np

            # Convert to numpy array
            img_array = np.array(img)

            # Convert to grayscale if color
            if len(img_array.shape) == 3:
                gray = np.mean(img_array, axis=2).astype(np.uint8)
            else:
                gray = img_array

            # Apply simple threshold to enhance contrast
            threshold = np.mean(gray)
            binary = np.where(gray > threshold, 255, 0).astype(np.uint8)

            return Image.fromarray(binary)
        except Exception:
            return None

    def _extract_instruments_from_text(self, text: str) -> List[ExtractedInstrument]:
        """Extract instrument tags from OCR text."""
        instruments = []
        lines = text.split('\n')

        for line in lines:
            # Clean up the line
            line = line.strip()
            if not line:
                continue

            # Try with original line
            instruments.extend(self._extract_from_line(line))

            # Also try with OCR-corrected line
            corrected_line = self._apply_ocr_corrections(line)
            if corrected_line != line:
                instruments.extend(self._extract_from_line(corrected_line))

        return instruments

    def _extract_from_line(self, line: str) -> List[ExtractedInstrument]:
        """Extract instruments from a single line."""
        instruments = []

        # Try each pattern
        for pattern in TAG_PATTERNS:
            matches = re.finditer(pattern, line, re.IGNORECASE)

            for match in matches:
                extracted = self._parse_match(match, line)
                if extracted:
                    instruments.append(extracted)

        # Also try to find instrument types followed by numbers even if not matching patterns
        instruments.extend(self._extract_by_instrument_type(line))

        return instruments

    def _extract_by_instrument_type(self, line: str) -> List[ExtractedInstrument]:
        """Try to find instruments by known type prefixes."""
        instruments = []
        line_upper = line.upper()

        # All known types including extended digital types
        all_types = INSTRUMENT_TYPES + EXTENDED_DIGITAL_TYPES

        for inst_type in all_types:
            # Find the type in the line
            pos = 0
            while True:
                idx = line_upper.find(inst_type, pos)
                if idx == -1:
                    break

                # Check what follows the type
                after = line_upper[idx + len(inst_type):]

                # Look for digits after the type (with optional dash/underscore)
                num_match = re.match(r'[-_]?(\d{3,4})', after)
                if num_match:
                    seq_num = num_match.group(1)

                    # Try to find area code before the type
                    before = line_upper[:idx]
                    area_match = re.search(r'(\d{3})[-]?$', before)
                    area = area_match.group(1) if area_match else self.default_area

                    # Try to find plant code
                    plant_match = re.search(r'([A-Z]{2}\d{2})[-]?' + re.escape(area) if area_match else r'([A-Z]{2}\d{2})[-]?', before)
                    plant_code = plant_match.group(1) if plant_match else self.default_plant_code

                    tag = f"{plant_code}-{area}-{inst_type}{seq_num.zfill(4)}"

                    instruments.append(ExtractedInstrument(
                        tag_number=tag,
                        instrument_type=inst_type,
                        confidence=0.6,  # Lower confidence for this method
                        source_text=line,
                        area=area,
                        service=None
                    ))

                pos = idx + 1

        return instruments

    def _apply_ocr_corrections(self, text: str) -> str:
        """Apply OCR corrections to text to fix common misreads."""
        corrected = text
        all_known_types = INSTRUMENT_TYPES + EXTENDED_INSTRUMENT_TYPES

        # First pass: Fix specific patterns where O is misread in tag numbers
        # e.g., LICO502 should be LIC0502, PDIO504 should be PDI0504
        # Look for known instrument types followed by O and digits
        for inst_type in sorted(all_known_types, key=len, reverse=True):
            # Pattern: TypeO### (e.g., LICO502, PDIO504, LADO511)
            pattern = re.compile(
                rf'({re.escape(inst_type)})([O])(\d{{3,4}})',
                re.IGNORECASE
            )
            corrected = pattern.sub(r'\g<1>0\3', corrected)

        # Second pass: Fix PP01 being OCR'd as PPO1
        corrected = re.sub(r'PPO1', 'PP01', corrected)
        corrected = re.sub(r'ppo1', 'PP01', corrected, flags=re.IGNORECASE)

        # Third pass: Fix O/0 in number sequences after instrument types
        # Pattern: Type-AreaCode-TypeNNNN or TypeNNNN
        for pattern in [
            r'([A-Z]{2}\d{2})-(\d{3})-([A-Z]{2,6})([O0I1lSsBb]\d{3})',  # Full format with leading OCR error
            r'([A-Z]{2,6})([O0I1lSsBb]\d{3})',  # Simple format with leading OCR error
        ]:
            for match in re.finditer(pattern, corrected, re.IGNORECASE):
                original = match.group(0)
                groups = match.groups()

                if len(groups) == 4:
                    plant, area, inst_type, num = groups
                    fixed_num = self._fix_ocr_number(num)
                    if fixed_num != num:
                        fixed = f"{plant}-{area}-{inst_type}{fixed_num}"
                        corrected = corrected.replace(original, fixed)
                elif len(groups) == 2:
                    inst_type, num = groups
                    if any(inst_type.upper() == t or inst_type.upper().startswith(t) for t in all_known_types):
                        fixed_num = self._fix_ocr_number(num)
                        if fixed_num != num:
                            fixed = f"{inst_type}{fixed_num}"
                            corrected = corrected.replace(original, fixed)

        return corrected

    def _fix_ocr_number(self, num_str: str) -> str:
        """Fix OCR errors in number string (O->0, I->1, etc.)."""
        fixed = num_str
        for wrong, right in [('O', '0'), ('o', '0'), ('I', '1'), ('i', '1'), ('l', '1'), ('S', '5'), ('s', '5'), ('B', '8'), ('b', '8')]:
            fixed = fixed.replace(wrong, right)
        return fixed

    def _parse_match(self, match: re.Match, source_line: str) -> Optional[ExtractedInstrument]:
        """Parse a regex match into an ExtractedInstrument."""
        groups = match.groups()

        # Determine format based on number of groups
        if len(groups) == 4:
            # Full format: PP01-364-TIT0001
            plant_code, area, inst_type, seq = groups
            tag = f"{plant_code.upper()}-{area}-{inst_type.upper()}{seq.zfill(4)}"
        elif len(groups) == 3:
            # Without plant code: 364-TIT0001 or 364TIT0001
            area, inst_type, seq = groups
            tag = f"{self.default_plant_code}-{area}-{inst_type.upper()}{seq.zfill(4)}"
        elif len(groups) == 2:
            # Simple format: TIT0001 or TIT-0001
            inst_type, seq = groups
            area = self.default_area
            tag = f"{self.default_plant_code}-{area}-{inst_type.upper()}{seq.zfill(4)}"
        else:
            return None

        # Validate instrument type
        inst_type_upper = inst_type.upper() if inst_type else ""

        # Check if it's a known instrument type (include extended digital types)
        all_known_types = INSTRUMENT_TYPES + EXTENDED_DIGITAL_TYPES
        is_valid_type = any(
            inst_type_upper.startswith(known_type) or inst_type_upper == known_type
            for known_type in all_known_types
        )

        if not is_valid_type:
            return None

        # Calculate confidence based on match quality
        confidence = self._calculate_confidence(match, source_line, inst_type_upper)

        # Try to extract service description from context
        service = self._extract_service(source_line, match)

        # Extract area from tag
        tag_parts = tag.split('-')
        area_code = tag_parts[1] if len(tag_parts) >= 2 else self.default_area

        return ExtractedInstrument(
            tag_number=tag,
            instrument_type=inst_type_upper,
            confidence=confidence,
            source_text=source_line,
            area=area_code,
            service=service
        )

    def _calculate_confidence(self, match: re.Match, line: str, inst_type: str) -> float:
        """Calculate confidence score for an extraction."""
        confidence = 0.5  # Base confidence

        # Higher confidence for known instrument types
        all_known_types = INSTRUMENT_TYPES + EXTENDED_DIGITAL_TYPES
        if inst_type in all_known_types:
            confidence += 0.3
        elif any(inst_type.startswith(t) for t in all_known_types):
            confidence += 0.2  # Partial match

        # Higher confidence for full tag format
        if len(match.groups()) == 4:
            confidence += 0.2
        elif len(match.groups()) == 3:
            confidence += 0.1  # Area + type + number format

        # Lower confidence if many special characters nearby
        context = line[max(0, match.start()-5):match.end()+5]
        special_chars = sum(1 for c in context if not c.isalnum() and c not in '-_')
        if special_chars > 3:
            confidence -= 0.1

        return min(max(confidence, 0.0), 1.0)

    def _extract_service(self, line: str, match: re.Match) -> Optional[str]:
        """Try to extract service description from the line."""
        # Get text after the tag
        after_tag = line[match.end():].strip()

        # Remove common delimiters
        after_tag = re.sub(r'^[\s\-:,]+', '', after_tag)

        # Take reasonable length of description
        if after_tag and len(after_tag) > 5:
            # Limit to first meaningful phrase
            service = after_tag[:50].strip()
            return service if service else None

        return None

    def _deduplicate_instruments(
        self,
        instruments: List[ExtractedInstrument]
    ) -> List[ExtractedInstrument]:
        """Remove duplicate instruments, keeping highest confidence."""
        seen = {}

        for inst in instruments:
            key = inst.tag_number.upper()
            if key not in seen or inst.confidence > seen[key].confidence:
                seen[key] = inst

        return list(seen.values())

    def to_instruments(self, extracted: List[ExtractedInstrument]) -> List[Instrument]:
        """Convert extracted instruments to Instrument model objects."""
        return [
            Instrument(
                tag_number=ext.tag_number,
                instrument_type=ext.instrument_type,
                service=ext.service or f"Extracted from PDF",
                area=ext.area or self.default_area
            )
            for ext in extracted
        ]


def extract_instruments_from_pdf(
    pdf_path: str,
    default_plant_code: str = "PP01",
    default_area: str = "000",
    min_confidence: float = 0.5
) -> List[Instrument]:
    """
    Convenience function to extract instruments from a PDF.

    Args:
        pdf_path: Path to PDF file
        default_plant_code: Default plant code
        default_area: Default area code
        min_confidence: Minimum confidence threshold

    Returns:
        List of Instrument objects
    """
    extractor = PDFExtractor(default_plant_code, default_area)
    result = extractor.extract_from_file(pdf_path)

    # Filter by confidence
    filtered = [
        ext for ext in result.instruments
        if ext.confidence >= min_confidence
    ]

    return extractor.to_instruments(filtered)


def get_pdf_page_as_image(pdf_path: str, page: int = 1, dpi: int = 150) -> Image.Image:
    """
    Get a specific page of a PDF as an image.

    Args:
        pdf_path: Path to PDF file
        page: Page number (1-indexed)
        dpi: Resolution

    Returns:
        PIL Image object
    """
    images = convert_from_path(pdf_path, dpi=dpi, first_page=page, last_page=page)
    return images[0] if images else None
