"""Instrument symbol drawing component."""

from typing import Tuple, Optional
from dataclasses import dataclass

from ..primitives import SVGCanvas, Point, DrawingStyle, STYLE_NORMAL, STYLE_THIN


@dataclass
class InstrumentSymbolConfig:
    """Configuration for instrument symbol."""
    width: float = 35
    height: float = 10
    font_size: float = 5
    wire_length: float = 15


def draw_instrument_symbol(
    canvas: SVGCanvas,
    position: Point,
    tag: str,
    config: Optional[InstrumentSymbolConfig] = None
) -> Tuple[Point, Point]:
    """
    Draw an instrument symbol with tag and wire connections.

    The symbol looks like:
    ┌─────────────────┐
    │ PP01-364-TIT0001│────┬─── + ─── WH
    └─────────────────┘    │
                          └─── - ─── BK

    Args:
        canvas: SVG canvas to draw on
        position: Top-left position of the symbol
        tag: Instrument tag number
        config: Optional configuration

    Returns:
        Tuple of (positive_wire_end, negative_wire_end) points
    """
    cfg = config or InstrumentSymbolConfig()

    # Draw instrument box
    canvas.draw_rect(position, cfg.width, cfg.height, STYLE_NORMAL)

    # Draw tag text inside box
    text_pos = Point(position.x + 2, position.y + cfg.height/2 + 1.5)
    style = DrawingStyle(font_size=cfg.font_size)
    canvas.draw_text(text_pos, tag, style)

    # Connection point on right side of box
    conn_x = position.x + cfg.width
    conn_y = position.y + cfg.height / 2

    # Draw horizontal line from box
    canvas.draw_horizontal_line(
        Point(conn_x, conn_y),
        5,
        STYLE_NORMAL
    )

    # Junction point
    junction = Point(conn_x + 5, conn_y)

    # Draw junction dot
    canvas.draw_circle(junction, 0.5, STYLE_NORMAL, fill="#000000")

    # Draw vertical line down from junction
    canvas.draw_vertical_line(junction, 4, STYLE_NORMAL)

    # Positive wire (top)
    pos_start = junction
    pos_end = Point(junction.x + cfg.wire_length, junction.y)
    canvas.draw_horizontal_line(pos_start, cfg.wire_length, STYLE_NORMAL)

    # Draw "+" label
    plus_label_pos = Point(pos_end.x - 8, pos_end.y - 1)
    canvas.draw_text(plus_label_pos, "+", DrawingStyle(font_size=4))

    # Draw wire color label
    color_pos = Point(pos_end.x - 3, pos_end.y - 1)
    canvas.draw_text(color_pos, "WH", DrawingStyle(font_size=3))

    # Negative wire (bottom)
    neg_start = Point(junction.x, junction.y + 4)
    neg_end = Point(neg_start.x + cfg.wire_length, neg_start.y)
    canvas.draw_horizontal_line(neg_start, cfg.wire_length, STYLE_NORMAL)

    # Draw "-" label
    minus_label_pos = Point(neg_end.x - 8, neg_end.y - 1)
    canvas.draw_text(minus_label_pos, "-", DrawingStyle(font_size=4))

    # Draw wire color label
    color_neg_pos = Point(neg_end.x - 3, neg_end.y - 1)
    canvas.draw_text(color_neg_pos, "BK", DrawingStyle(font_size=3))

    return (pos_end, neg_end)


def draw_instrument_row(
    canvas: SVGCanvas,
    position: Point,
    tag: str,
    row_height: float = 18,
    config: Optional[InstrumentSymbolConfig] = None
) -> dict:
    """
    Draw a complete instrument row with symbol and connections.

    Args:
        canvas: SVG canvas
        position: Starting position
        tag: Instrument tag
        row_height: Height of each row
        config: Optional configuration

    Returns:
        Dictionary with connection points and dimensions
    """
    cfg = config or InstrumentSymbolConfig()

    # Center the instrument vertically in the row
    symbol_y = position.y + (row_height - cfg.height) / 2

    pos_end, neg_end = draw_instrument_symbol(
        canvas,
        Point(position.x, symbol_y),
        tag,
        cfg
    )

    return {
        "positive_end": pos_end,
        "negative_end": neg_end,
        "row_height": row_height,
        "next_y": position.y + row_height,
    }
