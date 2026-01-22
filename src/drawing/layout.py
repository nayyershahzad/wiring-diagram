"""Page layout calculator for DCS interconnection diagrams."""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from .primitives import Point


@dataclass
class ZoneConfig:
    """Configuration for a drawing zone."""
    x_start_percent: float
    width_percent: float
    header: str


@dataclass
class PageLayout:
    """Layout configuration for a drawing page."""
    # Page dimensions (A3 landscape)
    width_mm: float = 420
    height_mm: float = 297

    # Margins
    margin_left: float = 20
    margin_right: float = 10
    margin_top: float = 10
    margin_bottom: float = 10

    # Title block
    title_block_height: float = 45

    # Drawing zones
    zones: Dict[str, ZoneConfig] = field(default_factory=dict)

    # Instruments per page
    instruments_per_page: int = 12
    row_height: float = 18

    def __post_init__(self):
        if not self.zones:
            self.zones = {
                "zone1_instrument": ZoneConfig(0.02, 0.15, "EPP-FIELD\nINSTRUMENT"),
                "zone2_junction_box": ZoneConfig(0.17, 0.25, "JUNCTION BOX"),
                "zone3_multipair": ZoneConfig(0.42, 0.13, "MULTIPAIR"),
                "zone4_cabinet": ZoneConfig(0.55, 0.30, "DCS (EPP) CCR\nMARSHALLING CABINET"),
                "zone5_notes": ZoneConfig(0.85, 0.15, "NOTES:"),
            }

    @property
    def drawing_width(self) -> float:
        """Available width for drawing content."""
        return self.width_mm - self.margin_left - self.margin_right

    @property
    def drawing_height(self) -> float:
        """Available height for drawing content (excluding title block)."""
        return self.height_mm - self.margin_top - self.margin_bottom - self.title_block_height

    @property
    def content_start(self) -> Point:
        """Top-left corner of the drawing content area."""
        return Point(self.margin_left, self.margin_top)

    @property
    def title_block_position(self) -> Point:
        """Top-left corner of the title block."""
        return Point(
            self.margin_left,
            self.height_mm - self.margin_bottom - self.title_block_height
        )

    def get_zone_x(self, zone_name: str) -> float:
        """Get the X coordinate for a zone."""
        if zone_name not in self.zones:
            return self.margin_left

        zone = self.zones[zone_name]
        return self.margin_left + self.drawing_width * zone.x_start_percent

    def get_zone_width(self, zone_name: str) -> float:
        """Get the width for a zone."""
        if zone_name not in self.zones:
            return 0

        zone = self.zones[zone_name]
        return self.drawing_width * zone.width_percent

    def get_zone_rect(self, zone_name: str) -> Dict[str, float]:
        """Get the rectangle for a zone."""
        x = self.get_zone_x(zone_name)
        width = self.get_zone_width(zone_name)

        return {
            "x": x,
            "y": self.margin_top,
            "width": width,
            "height": self.drawing_height,
        }


class LayoutCalculator:
    """Calculator for positioning drawing elements."""

    def __init__(self, layout: Optional[PageLayout] = None):
        """
        Initialize the layout calculator.

        Args:
            layout: Optional page layout configuration
        """
        self.layout = layout or PageLayout()

    def calculate_instrument_positions(
        self,
        count: int,
        start_y: Optional[float] = None
    ) -> List[Point]:
        """
        Calculate positions for instrument symbols.

        Args:
            count: Number of instruments
            start_y: Optional starting Y position

        Returns:
            List of positions for each instrument
        """
        zone_x = self.layout.get_zone_x("zone1_instrument")
        y = start_y or self.layout.margin_top + 20  # Leave space for header

        positions = []
        for i in range(count):
            positions.append(Point(zone_x + 5, y))
            y += self.layout.row_height

        return positions

    def calculate_jb_position(self) -> Point:
        """Calculate position for junction box."""
        zone_rect = self.layout.get_zone_rect("zone2_junction_box")
        return Point(
            zone_rect["x"] + 10,
            zone_rect["y"] + 25  # Below header
        )

    def calculate_multipair_position(self) -> Point:
        """Calculate position for multipair cable box."""
        zone_rect = self.layout.get_zone_rect("zone3_multipair")
        # Center vertically in the zone
        center_y = zone_rect["y"] + zone_rect["height"] / 2
        return Point(
            zone_rect["x"] + 5,
            center_y - 15  # Adjust for cable box height
        )

    def calculate_cabinet_position(self) -> Point:
        """Calculate position for marshalling cabinet."""
        zone_rect = self.layout.get_zone_rect("zone4_cabinet")
        return Point(
            zone_rect["x"] + 5,
            zone_rect["y"] + 25  # Below header
        )

    def calculate_notes_position(self) -> Point:
        """Calculate position for notes section."""
        zone_rect = self.layout.get_zone_rect("zone5_notes")
        return Point(
            zone_rect["x"] + 5,
            zone_rect["y"] + 25
        )

    def calculate_pages_needed(self, instrument_count: int) -> int:
        """
        Calculate number of pages needed for instruments.

        Args:
            instrument_count: Total number of instruments

        Returns:
            Number of pages needed
        """
        import math
        return math.ceil(instrument_count / self.layout.instruments_per_page)

    def get_instruments_for_page(
        self,
        instruments: list,
        page_number: int
    ) -> list:
        """
        Get instruments for a specific page.

        Args:
            instruments: Full list of instruments
            page_number: Page number (1-based)

        Returns:
            List of instruments for the page
        """
        start_idx = (page_number - 1) * self.layout.instruments_per_page
        end_idx = start_idx + self.layout.instruments_per_page
        return instruments[start_idx:end_idx]


def create_default_layout() -> PageLayout:
    """Create a default page layout."""
    return PageLayout()


def calculate_wire_routes(
    instrument_positions: List[Point],
    jb_position: Point,
    cable_position: Point,
    cabinet_position: Point
) -> List[Dict[str, Any]]:
    """
    Calculate wire routing between components.

    Args:
        instrument_positions: List of instrument positions
        jb_position: JB position
        cable_position: Multipair cable position
        cabinet_position: Cabinet position

    Returns:
        List of wire route dictionaries
    """
    routes = []

    # This would calculate the actual wire routing
    # For now, return basic structure
    for i, inst_pos in enumerate(instrument_positions):
        routes.append({
            "instrument_index": i,
            "instrument_to_jb": {
                "start": inst_pos,
                "waypoints": [],
                "end": jb_position,
            },
            "jb_to_cable": {
                "start": jb_position,
                "waypoints": [],
                "end": cable_position,
            },
            "cable_to_cabinet": {
                "start": cable_position,
                "waypoints": [],
                "end": cabinet_position,
            },
        })

    return routes
