"""Drawing data models for DCS interconnection diagrams."""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date

from .instrument import Instrument
from .cable import MultipairCable
from .terminal import JunctionBox, MarshallingCabinet


@dataclass
class DrawingMetadata:
    """Metadata for a drawing."""

    drawing_number: str          # e.g., "100478CP-N-PG-PP01-IC-DIC-0004-004"
    title: str                   # e.g., "PP01-601-IAJB0002 (ANALOG JB)"
    revision: str = "0"
    revision_date: str = ""
    project_number: str = "100478"
    project_name: str = "EARLY POWER PLANT\nRUMAILA OIL FIELD"
    company: str = "CHINA PETROLEUM ENGINEERING & CONSTRUCTION CORP."
    drawn_by: str = ""
    checked_by: str = ""
    approved_by: str = ""
    scale: str = "NTS"           # Not To Scale

    def __post_init__(self):
        if not self.revision_date:
            self.revision_date = date.today().strftime("%Y-%m-%d")


@dataclass
class DrawingSheet:
    """Represents a single sheet of the interconnection diagram."""

    sheet_number: int
    metadata: DrawingMetadata
    instruments: List[Instrument] = field(default_factory=list)
    junction_box: Optional[JunctionBox] = None
    multipair_cable: Optional[MultipairCable] = None
    marshalling_cabinet: Optional[MarshallingCabinet] = None
    notes: List[str] = field(default_factory=list)

    @property
    def instrument_count(self) -> int:
        """Number of instruments on this sheet."""
        return len(self.instruments)

    def add_instrument(self, instrument: Instrument):
        """Add an instrument to the sheet."""
        self.instruments.append(instrument)

    def add_note(self, note: str):
        """Add a note to the sheet."""
        self.notes.append(note)


@dataclass
class InterconnectionDrawing:
    """Represents a complete interconnection drawing with multiple sheets."""

    base_drawing_number: str     # Base drawing number without sheet suffix
    title: str
    sheets: List[DrawingSheet] = field(default_factory=list)
    metadata: Optional[DrawingMetadata] = None

    @property
    def sheet_count(self) -> int:
        """Total number of sheets."""
        return len(self.sheets)

    @property
    def total_instruments(self) -> int:
        """Total instruments across all sheets."""
        return sum(sheet.instrument_count for sheet in self.sheets)

    def add_sheet(self, sheet: DrawingSheet):
        """Add a sheet to the drawing."""
        self.sheets.append(sheet)

    def get_sheet(self, sheet_number: int) -> Optional[DrawingSheet]:
        """Get sheet by number."""
        for sheet in self.sheets:
            if sheet.sheet_number == sheet_number:
                return sheet
        return None

    def generate_drawing_numbers(self):
        """Generate drawing numbers for all sheets."""
        for i, sheet in enumerate(self.sheets, start=1):
            sheet.metadata.drawing_number = f"{self.base_drawing_number}-{i:03d}"


@dataclass
class DrawingProject:
    """Represents a complete project with multiple interconnection drawings."""

    project_number: str
    project_name: str
    drawings: List[InterconnectionDrawing] = field(default_factory=list)

    def add_drawing(self, drawing: InterconnectionDrawing):
        """Add a drawing to the project."""
        self.drawings.append(drawing)

    @property
    def total_sheets(self) -> int:
        """Total sheets across all drawings."""
        return sum(d.sheet_count for d in self.drawings)
