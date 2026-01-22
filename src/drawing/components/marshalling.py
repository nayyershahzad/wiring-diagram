"""Marshalling Cabinet drawing component."""

from typing import List, Optional
from dataclasses import dataclass

from ..primitives import SVGCanvas, Point, DrawingStyle, STYLE_NORMAL, STYLE_THIN, STYLE_THICK
from ...models import TerminalAllocation, TerminalStatus


@dataclass
class CabinetDrawingConfig:
    """Configuration for cabinet drawing."""
    width: float = 80
    header_height: float = 15
    tb_header_height: float = 10
    terminal_row_height: float = 8
    margin: float = 3
    font_size_header: float = 6
    font_size_tb: float = 5
    font_size_terminal: float = 4


def draw_marshalling_cabinet(
    canvas: SVGCanvas,
    position: Point,
    cabinet_tag: str,
    tb_tag: str,
    allocations: List[TerminalAllocation],
    config: Optional[CabinetDrawingConfig] = None
) -> dict:
    """
    Draw a marshalling cabinet with terminal block.

    The cabinet looks like:
    ┌─────────────────────────────────┐
    │      PP01-601-ICP001            │
    ├─────────────────────────────────┤
    │      TB601-I0004                │
    ├─────────────────────────────────┤
    │                      DCS TAG    │
    │  PR1 ○──┬─ WH ── 1+ ─┐         │
    │         └─ BK ── 1- ─┴─ PP01-TIT0001
    │  PR2 ○──┬─ WH ── 2+ ─┐         │
    │         └─ BK ── 2- ─┴─ PP01-PIT0001
    │         ...                     │
    │                                 │
    │      0S ────────────────────────│ ← INSTRUMENT
    │         ◎                       │   EARTH BAR
    └─────────────────────────────────┘

    Args:
        canvas: SVG canvas
        position: Top-left position
        cabinet_tag: Cabinet tag
        tb_tag: Terminal block tag
        allocations: List of terminal allocations
        config: Optional configuration

    Returns:
        Dictionary with connection points
    """
    cfg = config or CabinetDrawingConfig()

    # Calculate total height
    num_terminals = len(allocations)
    content_height = num_terminals * cfg.terminal_row_height + cfg.margin * 2
    total_height = cfg.header_height + cfg.tb_header_height + content_height + 15

    # Draw main cabinet box
    canvas.draw_rect(position, cfg.width, total_height, STYLE_NORMAL)

    # Draw cabinet header
    canvas.draw_text(
        Point(position.x + cfg.width/2, position.y + 8),
        cabinet_tag,
        DrawingStyle(font_size=cfg.font_size_header),
        anchor="middle"
    )

    # Draw header line
    header_y = position.y + cfg.header_height
    canvas.draw_horizontal_line(Point(position.x, header_y), cfg.width, STYLE_NORMAL)

    # Draw TB header
    canvas.draw_text(
        Point(position.x + cfg.width/2, header_y + 7),
        tb_tag,
        DrawingStyle(font_size=cfg.font_size_tb),
        anchor="middle"
    )

    # Draw TB header line
    tb_header_y = header_y + cfg.tb_header_height
    canvas.draw_horizontal_line(Point(position.x, tb_header_y), cfg.width, STYLE_NORMAL)

    # Draw "DCS TAG" header
    canvas.draw_text(
        Point(position.x + cfg.width - 15, tb_header_y + 5),
        "DCS TAG",
        DrawingStyle(font_size=3),
        anchor="middle"
    )

    # Draw terminals
    left_connections = []
    terminal_y = tb_header_y + cfg.margin + 8

    for idx, alloc in enumerate(allocations):
        # Pair label on left
        canvas.draw_text(
            Point(position.x + 5, terminal_y),
            alloc.terminal_pair or f"PR{alloc.terminal_number}",
            DrawingStyle(font_size=cfg.font_size_terminal)
        )

        # Left terminal circle
        left_x = position.x + 15
        left_point = Point(left_x, terminal_y)
        canvas.draw_terminal_circle(left_point)
        left_connections.append((alloc.instrument_tag, left_point))

        # Wire color and terminal labels
        label_x = left_x + 8

        # Positive wire
        canvas.draw_text(
            Point(label_x, terminal_y - 1),
            f"{alloc.wire_color_positive} ── {alloc.terminal_positive}",
            DrawingStyle(font_size=3)
        )

        # Draw connection to positive
        canvas.draw_horizontal_line(
            Point(left_x + 2, terminal_y),
            20,
            STYLE_THIN
        )

        # Junction for positive/negative
        junction_x = left_x + 25

        # Negative wire (offset down)
        neg_y = terminal_y + 3
        canvas.draw_text(
            Point(label_x, neg_y - 1),
            f"{alloc.wire_color_negative} ── {alloc.terminal_negative}",
            DrawingStyle(font_size=3)
        )

        # Draw connection line
        canvas.draw_horizontal_line(
            Point(left_x + 8, neg_y),
            17,
            STYLE_THIN
        )

        # Draw vertical connector
        canvas.draw_vertical_line(
            Point(junction_x, terminal_y),
            3,
            STYLE_THIN
        )

        # DCS tag / Instrument tag on right
        if alloc.status == TerminalStatus.USED:
            dcs_tag = alloc.dcs_tag or alloc.instrument_tag
            # Shorten tag for display
            short_tag = dcs_tag.split("-")[-1] if dcs_tag and "-" in dcs_tag else dcs_tag
            canvas.draw_text(
                Point(junction_x + 5, terminal_y + 1),
                short_tag or "",
                DrawingStyle(font_size=3)
            )
        else:
            canvas.draw_text(
                Point(junction_x + 5, terminal_y + 1),
                "SPARE",
                DrawingStyle(font_size=3)
            )

        terminal_y += cfg.terminal_row_height

    # Draw overall shield / earth bar at bottom
    shield_y = terminal_y + 5
    canvas.draw_text(
        Point(position.x + 5, shield_y),
        "0S",
        DrawingStyle(font_size=cfg.font_size_terminal)
    )
    canvas.draw_horizontal_line(
        Point(position.x + 12, shield_y),
        cfg.width - 17,
        STYLE_THIN
    )

    # Draw earth symbol
    earth_x = position.x + cfg.width - 10
    canvas.draw_text(
        Point(earth_x, shield_y + 6),
        "INSTRUMENT",
        DrawingStyle(font_size=3)
    )
    canvas.draw_text(
        Point(earth_x, shield_y + 10),
        "EARTH BAR",
        DrawingStyle(font_size=3)
    )

    return {
        "left_connections": left_connections,
        "width": cfg.width,
        "height": total_height,
        "bottom_y": position.y + total_height,
    }


def draw_cabinet_compact(
    canvas: SVGCanvas,
    position: Point,
    cabinet_tag: str,
    tb_count: int,
    terminal_count: int,
    config: Optional[CabinetDrawingConfig] = None
) -> dict:
    """
    Draw a compact cabinet representation for overview drawings.

    Args:
        canvas: SVG canvas
        position: Top-left position
        cabinet_tag: Cabinet tag
        tb_count: Number of terminal blocks
        terminal_count: Total terminals

    Returns:
        Dictionary with connection points
    """
    cfg = config or CabinetDrawingConfig()

    width = 50
    height = 30

    # Draw box
    canvas.draw_rect(position, width, height, STYLE_NORMAL)

    # Draw tag
    canvas.draw_text(
        Point(position.x + width/2, position.y + 10),
        cabinet_tag,
        DrawingStyle(font_size=5),
        anchor="middle"
    )

    # Draw info
    canvas.draw_text(
        Point(position.x + width/2, position.y + 18),
        f"{tb_count} TB",
        DrawingStyle(font_size=4),
        anchor="middle"
    )
    canvas.draw_text(
        Point(position.x + width/2, position.y + 24),
        f"{terminal_count} terminals",
        DrawingStyle(font_size=4),
        anchor="middle"
    )

    return {
        "left_connection": Point(position.x, position.y + height/2),
        "width": width,
        "height": height,
    }
