"""SVG drawing primitives for DCS interconnection diagram generator."""

import svgwrite
from typing import Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class Point:
    """2D point."""
    x: float
    y: float

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass
class DrawingStyle:
    """Drawing style configuration."""
    stroke: str = "#000000"
    stroke_width: float = 0.5
    fill: str = "none"
    font_family: str = "Arial"
    font_size: float = 8


# Default styles
STYLE_NORMAL = DrawingStyle()
STYLE_THIN = DrawingStyle(stroke_width=0.25)
STYLE_THICK = DrawingStyle(stroke_width=1.0)
STYLE_BORDER = DrawingStyle(stroke_width=0.7)


def mm_to_px(mm: float, dpi: float = 96) -> float:
    """Convert millimeters to pixels."""
    return mm * dpi / 25.4


def px_to_mm(px: float, dpi: float = 96) -> float:
    """Convert pixels to millimeters."""
    return px * 25.4 / dpi


class SVGCanvas:
    """SVG canvas for drawing interconnection diagrams."""

    def __init__(
        self,
        width_mm: float = 420,
        height_mm: float = 297,
        filename: str = "drawing.svg"
    ):
        """
        Initialize SVG canvas.

        Args:
            width_mm: Width in millimeters (default A3 landscape)
            height_mm: Height in millimeters
            filename: Output filename
        """
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.filename = filename

        # Create SVG drawing with mm units
        self.dwg = svgwrite.Drawing(
            filename=filename,
            size=(f"{width_mm}mm", f"{height_mm}mm"),
            viewBox=f"0 0 {width_mm} {height_mm}"
        )

        # Add definitions for common elements
        self._add_definitions()

    def _add_definitions(self):
        """Add common definitions (markers, patterns, etc.)."""
        # Arrowhead marker
        marker = self.dwg.marker(
            id="arrowhead",
            insert=(5, 5),
            size=(10, 10),
            orient="auto"
        )
        marker.add(self.dwg.polygon(
            points=[(0, 0), (10, 5), (0, 10), (3, 5)],
            fill="#000000"
        ))
        self.dwg.defs.add(marker)

        # Circle marker for terminals
        circle_marker = self.dwg.marker(
            id="terminal",
            insert=(3, 3),
            size=(6, 6)
        )
        circle_marker.add(self.dwg.circle(
            center=(3, 3),
            r=2,
            stroke="#000000",
            stroke_width=0.3,
            fill="white"
        ))
        self.dwg.defs.add(circle_marker)

    def draw_line(
        self,
        start: Point,
        end: Point,
        style: DrawingStyle = STYLE_NORMAL
    ):
        """Draw a line."""
        self.dwg.add(self.dwg.line(
            start=start.to_tuple(),
            end=end.to_tuple(),
            stroke=style.stroke,
            stroke_width=style.stroke_width
        ))

    def draw_rect(
        self,
        origin: Point,
        width: float,
        height: float,
        style: DrawingStyle = STYLE_NORMAL,
        fill: Optional[str] = None
    ):
        """Draw a rectangle."""
        self.dwg.add(self.dwg.rect(
            insert=origin.to_tuple(),
            size=(width, height),
            stroke=style.stroke,
            stroke_width=style.stroke_width,
            fill=fill or style.fill
        ))

    def draw_circle(
        self,
        center: Point,
        radius: float,
        style: DrawingStyle = STYLE_NORMAL,
        fill: Optional[str] = None
    ):
        """Draw a circle."""
        self.dwg.add(self.dwg.circle(
            center=center.to_tuple(),
            r=radius,
            stroke=style.stroke,
            stroke_width=style.stroke_width,
            fill=fill or style.fill
        ))

    def draw_text(
        self,
        position: Point,
        text: str,
        style: DrawingStyle = STYLE_NORMAL,
        anchor: str = "start",
        rotation: float = 0
    ):
        """
        Draw text.

        Args:
            position: Text position
            text: Text content
            style: Drawing style
            anchor: Text anchor (start, middle, end)
            rotation: Rotation angle in degrees
        """
        text_elem = self.dwg.text(
            text,
            insert=position.to_tuple(),
            font_family=style.font_family,
            font_size=f"{style.font_size}pt",
            text_anchor=anchor,
            fill=style.stroke
        )

        if rotation != 0:
            text_elem.rotate(rotation, center=position.to_tuple())

        self.dwg.add(text_elem)

    def draw_polyline(
        self,
        points: List[Point],
        style: DrawingStyle = STYLE_NORMAL
    ):
        """Draw a polyline through points."""
        point_tuples = [p.to_tuple() for p in points]
        self.dwg.add(self.dwg.polyline(
            points=point_tuples,
            stroke=style.stroke,
            stroke_width=style.stroke_width,
            fill="none"
        ))

    def draw_horizontal_line(
        self,
        start: Point,
        length: float,
        style: DrawingStyle = STYLE_NORMAL
    ):
        """Draw a horizontal line."""
        end = Point(start.x + length, start.y)
        self.draw_line(start, end, style)

    def draw_vertical_line(
        self,
        start: Point,
        length: float,
        style: DrawingStyle = STYLE_NORMAL
    ):
        """Draw a vertical line."""
        end = Point(start.x, start.y + length)
        self.draw_line(start, end, style)

    def draw_terminal_circle(
        self,
        center: Point,
        radius: float = 1.5,
        filled: bool = False
    ):
        """Draw a terminal connection circle."""
        self.draw_circle(
            center=center,
            radius=radius,
            style=STYLE_THIN,
            fill="#000000" if filled else "white"
        )

    def draw_wire(
        self,
        start: Point,
        end: Point,
        with_terminals: bool = True
    ):
        """Draw a wire connection with optional terminal circles."""
        self.draw_line(start, end, STYLE_NORMAL)

        if with_terminals:
            self.draw_terminal_circle(start, filled=True)
            self.draw_terminal_circle(end, filled=True)

    def add_group(self, id: str = None):
        """Create and return a group element."""
        group = self.dwg.g(id=id)
        self.dwg.add(group)
        return group

    def save(self, filename: Optional[str] = None):
        """Save the SVG file."""
        if filename:
            self.dwg.filename = filename
        self.dwg.save()

    def tostring(self) -> str:
        """Return SVG as string."""
        return self.dwg.tostring()


def create_instrument_symbol(
    canvas: SVGCanvas,
    position: Point,
    tag: str,
    width: float = 30,
    height: float = 8
) -> Point:
    """
    Draw an instrument symbol.

    Returns the connection point (right side of symbol).
    """
    # Draw box
    canvas.draw_rect(position, width, height, STYLE_NORMAL)

    # Draw tag text
    text_pos = Point(position.x + width/2, position.y + height/2 + 2)
    style = DrawingStyle(font_size=5)
    canvas.draw_text(text_pos, tag, style, anchor="middle")

    # Connection point
    return Point(position.x + width, position.y + height/2)


def create_terminal_pair(
    canvas: SVGCanvas,
    position: Point,
    label_positive: str,
    label_negative: str,
    wire_color_pos: str = "WH",
    wire_color_neg: str = "BK",
    spacing: float = 4
) -> Tuple[Point, Point]:
    """
    Draw a terminal pair (positive and negative).

    Returns tuple of (positive_connection, negative_connection) points.
    """
    # Positive terminal
    pos_center = Point(position.x, position.y)
    canvas.draw_terminal_circle(pos_center)

    # Draw positive label
    label_style = DrawingStyle(font_size=4)
    canvas.draw_text(
        Point(pos_center.x + 3, pos_center.y + 1),
        label_positive,
        label_style
    )

    # Negative terminal
    neg_center = Point(position.x, position.y + spacing)
    canvas.draw_terminal_circle(neg_center)

    # Draw negative label
    canvas.draw_text(
        Point(neg_center.x + 3, neg_center.y + 1),
        label_negative,
        label_style
    )

    return (pos_center, neg_center)
