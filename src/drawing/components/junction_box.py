"""Junction Box drawing component."""

from typing import List, Optional, Tuple
from dataclasses import dataclass

from ..primitives import SVGCanvas, Point, DrawingStyle, STYLE_NORMAL, STYLE_THIN, STYLE_THICK
from ...models import TerminalAllocation, TerminalStatus


@dataclass
class JBDrawingConfig:
    """Configuration for JB drawing."""
    width: float = 60
    header_height: float = 12
    terminal_row_height: float = 8
    terminal_spacing: float = 8
    margin: float = 3
    font_size_header: float = 6
    font_size_terminal: float = 4


def draw_junction_box(
    canvas: SVGCanvas,
    position: Point,
    jb_tag: str,
    allocations: List[TerminalAllocation],
    config: Optional[JBDrawingConfig] = None
) -> dict:
    """
    Draw a junction box with terminal allocations.

    The JB looks like:
    ┌─────────────────────────────────┐
    │      PP01-601-IAJB0002          │
    ├─────────────────────────────────┤
    │                                 │
    │  ○─┬─ 1+ ────────── WH ───○     │
    │    └─ 1- ────────── BK ───○     │
    │      1S ─┐                      │
    │  ○─┬─ 2+ ────────── WH ───○     │
    │    └─ 2- ────────── BK ───○     │
    │      2S ─┤                      │
    │         ...                     │
    │      0S ─┴───────────────────── │ ← To Earth Bar
    └─────────────────────────────────┘

    Args:
        canvas: SVG canvas
        position: Top-left position
        jb_tag: Junction box tag
        allocations: List of terminal allocations
        config: Optional configuration

    Returns:
        Dictionary with connection points
    """
    cfg = config or JBDrawingConfig()

    # Calculate total height
    num_terminals = len(allocations)
    content_height = num_terminals * cfg.terminal_row_height + cfg.margin * 2
    total_height = cfg.header_height + content_height + 10  # Extra for shield

    # Draw main box
    canvas.draw_rect(position, cfg.width, total_height, STYLE_NORMAL)

    # Draw header line
    header_line_y = position.y + cfg.header_height
    canvas.draw_horizontal_line(
        Point(position.x, header_line_y),
        cfg.width,
        STYLE_NORMAL
    )

    # Draw JB tag in header
    header_text_pos = Point(
        position.x + cfg.width / 2,
        position.y + cfg.header_height / 2 + 2
    )
    canvas.draw_text(
        header_text_pos,
        jb_tag,
        DrawingStyle(font_size=cfg.font_size_header),
        anchor="middle"
    )

    # Draw terminals
    left_connections = []
    right_connections = []
    terminal_y = header_line_y + cfg.margin + 4

    for idx, alloc in enumerate(allocations):
        # Left side terminal circle (from instrument)
        left_x = position.x + 5
        left_point = Point(left_x, terminal_y)
        canvas.draw_terminal_circle(left_point)
        left_connections.append((alloc.instrument_tag, left_point))

        # Terminal labels
        label_x = left_x + 8
        label_style = DrawingStyle(font_size=cfg.font_size_terminal)

        # Positive terminal label
        canvas.draw_text(
            Point(label_x, terminal_y - 0.5),
            alloc.terminal_positive,
            label_style
        )

        # Draw connection line
        line_start = Point(left_x + 2, terminal_y)
        line_mid = Point(position.x + cfg.width / 2, terminal_y)
        canvas.draw_horizontal_line(line_start, cfg.width / 2 - 10, STYLE_THIN)

        # Wire color
        color_x = position.x + cfg.width / 2 + 5
        canvas.draw_text(
            Point(color_x, terminal_y - 0.5),
            alloc.wire_color_positive,
            DrawingStyle(font_size=3)
        )

        # Right side terminal circle (to multipair)
        right_x = position.x + cfg.width - 5
        right_point = Point(right_x, terminal_y)
        canvas.draw_terminal_circle(right_point)
        right_connections.append((alloc.instrument_tag, right_point, "positive"))

        # Continue line to right terminal
        canvas.draw_horizontal_line(
            Point(color_x + 8, terminal_y),
            right_x - color_x - 10,
            STYLE_THIN
        )

        # Negative terminal (same row, offset down slightly)
        neg_y = terminal_y + 3

        # Negative terminal label
        canvas.draw_text(
            Point(label_x, neg_y - 0.5),
            alloc.terminal_negative,
            label_style
        )

        # Negative wire
        canvas.draw_horizontal_line(
            Point(left_x + 12, neg_y),
            cfg.width / 2 - 17,
            STYLE_THIN
        )

        # Negative wire color
        canvas.draw_text(
            Point(color_x, neg_y - 0.5),
            alloc.wire_color_negative,
            DrawingStyle(font_size=3)
        )

        # Negative right terminal
        neg_right_point = Point(right_x, neg_y)
        canvas.draw_terminal_circle(neg_right_point)
        right_connections.append((alloc.instrument_tag, neg_right_point, "negative"))

        canvas.draw_horizontal_line(
            Point(color_x + 8, neg_y),
            right_x - color_x - 10,
            STYLE_THIN
        )

        # Mark spare terminals differently
        if alloc.status == TerminalStatus.SPARE:
            spare_label = Point(position.x + cfg.width - 15, terminal_y + 1)
            canvas.draw_text(spare_label, "SPARE", DrawingStyle(font_size=3))

        terminal_y += cfg.terminal_row_height

    # Draw overall shield line at bottom
    shield_y = terminal_y + 3
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

    return {
        "left_connections": left_connections,
        "right_connections": right_connections,
        "width": cfg.width,
        "height": total_height,
        "bottom_y": position.y + total_height,
    }


def draw_jb_compact(
    canvas: SVGCanvas,
    position: Point,
    jb_tag: str,
    terminal_count: int,
    config: Optional[JBDrawingConfig] = None
) -> dict:
    """
    Draw a compact JB representation for overview drawings.

    Args:
        canvas: SVG canvas
        position: Top-left position
        jb_tag: Junction box tag
        terminal_count: Number of terminals

    Returns:
        Dictionary with connection points
    """
    cfg = config or JBDrawingConfig()

    width = 40
    height = 25

    # Draw box
    canvas.draw_rect(position, width, height, STYLE_NORMAL)

    # Draw tag
    canvas.draw_text(
        Point(position.x + width/2, position.y + 10),
        jb_tag,
        DrawingStyle(font_size=5),
        anchor="middle"
    )

    # Draw terminal count
    canvas.draw_text(
        Point(position.x + width/2, position.y + 18),
        f"({terminal_count} terminals)",
        DrawingStyle(font_size=4),
        anchor="middle"
    )

    return {
        "left_connection": Point(position.x, position.y + height/2),
        "right_connection": Point(position.x + width, position.y + height/2),
        "width": width,
        "height": height,
    }
