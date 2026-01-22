"""Cable drawing component."""

from typing import Optional, List
from dataclasses import dataclass

from ..primitives import SVGCanvas, Point, DrawingStyle, STYLE_NORMAL, STYLE_THIN


@dataclass
class CableDrawingConfig:
    """Configuration for cable drawing."""
    width: float = 30
    font_size: float = 5


def draw_multipair_cable(
    canvas: SVGCanvas,
    position: Point,
    cable_tag: str,
    specification: str,
    pair_count: int,
    used_pairs: int,
    config: Optional[CableDrawingConfig] = None
) -> dict:
    """
    Draw a multipair cable representation.

    The cable looks like:
           ┌───────────┐
           │ I0004     │
    ═══════│5PRx1.0mm2 │═══════
           │ (4/5)     │
           └───────────┘

    Args:
        canvas: SVG canvas
        position: Top-left position of the cable box
        cable_tag: Cable tag number (e.g., "PP01-601-I0004")
        specification: Cable specification (e.g., "5PRx1.0mm2")
        pair_count: Total pairs in cable
        used_pairs: Number of used pairs
        config: Optional configuration

    Returns:
        Dictionary with connection points
    """
    cfg = config or CableDrawingConfig()

    box_width = cfg.width
    box_height = 25

    # Draw cable box
    canvas.draw_rect(position, box_width, box_height, STYLE_NORMAL)

    # Draw cable tag (short version)
    short_tag = cable_tag.split("-")[-1] if "-" in cable_tag else cable_tag
    canvas.draw_text(
        Point(position.x + box_width/2, position.y + 7),
        short_tag,
        DrawingStyle(font_size=cfg.font_size),
        anchor="middle"
    )

    # Draw specification
    canvas.draw_text(
        Point(position.x + box_width/2, position.y + 13),
        specification,
        DrawingStyle(font_size=4),
        anchor="middle"
    )

    # Draw usage (used/total)
    canvas.draw_text(
        Point(position.x + box_width/2, position.y + 19),
        f"({used_pairs}/{pair_count})",
        DrawingStyle(font_size=4),
        anchor="middle"
    )

    # Draw cable lines on both sides
    cable_y = position.y + box_height / 2

    # Left cable line (double line for multipair)
    left_line_length = 10
    canvas.draw_horizontal_line(
        Point(position.x - left_line_length, cable_y - 1),
        left_line_length,
        STYLE_NORMAL
    )
    canvas.draw_horizontal_line(
        Point(position.x - left_line_length, cable_y + 1),
        left_line_length,
        STYLE_NORMAL
    )

    # Right cable line
    right_line_length = 10
    right_start = position.x + box_width
    canvas.draw_horizontal_line(
        Point(right_start, cable_y - 1),
        right_line_length,
        STYLE_NORMAL
    )
    canvas.draw_horizontal_line(
        Point(right_start, cable_y + 1),
        right_line_length,
        STYLE_NORMAL
    )

    return {
        "left_connection": Point(position.x - left_line_length, cable_y),
        "right_connection": Point(right_start + right_line_length, cable_y),
        "center": Point(position.x + box_width/2, cable_y),
        "width": box_width,
        "height": box_height,
    }


def draw_cable_run(
    canvas: SVGCanvas,
    start: Point,
    end: Point,
    with_arrows: bool = False
):
    """
    Draw a cable run between two points.

    Args:
        canvas: SVG canvas
        start: Starting point
        end: Ending point
        with_arrows: Whether to draw arrows at the ends
    """
    # Draw horizontal line to midpoint, then vertical, then horizontal
    mid_x = (start.x + end.x) / 2

    # First horizontal segment
    canvas.draw_horizontal_line(start, mid_x - start.x, STYLE_NORMAL)

    # Vertical segment if needed
    if start.y != end.y:
        canvas.draw_vertical_line(Point(mid_x, start.y), end.y - start.y, STYLE_NORMAL)

    # Second horizontal segment
    canvas.draw_horizontal_line(Point(mid_x, end.y), end.x - mid_x, STYLE_NORMAL)


def draw_branch_cable(
    canvas: SVGCanvas,
    start: Point,
    end: Point,
    cable_tag: str,
    show_tag: bool = False
):
    """
    Draw a branch cable (single pair) connection.

    Args:
        canvas: SVG canvas
        start: Starting point (instrument side)
        end: Ending point (JB side)
        cable_tag: Cable tag number
        show_tag: Whether to show the cable tag
    """
    canvas.draw_line(start, end, STYLE_THIN)

    if show_tag:
        # Draw tag at midpoint
        mid_x = (start.x + end.x) / 2
        mid_y = (start.y + end.y) / 2
        canvas.draw_text(
            Point(mid_x, mid_y - 2),
            cable_tag,
            DrawingStyle(font_size=3),
            anchor="middle"
        )


def draw_wire_pair(
    canvas: SVGCanvas,
    start_pos: Point,
    start_neg: Point,
    end_pos: Point,
    end_neg: Point,
    pair_number: int = 1
):
    """
    Draw a wire pair with pair number label.

    Args:
        canvas: SVG canvas
        start_pos: Start positive terminal
        start_neg: Start negative terminal
        end_pos: End positive terminal
        end_neg: End negative terminal
        pair_number: Pair number for labeling
    """
    # Draw positive wire
    canvas.draw_line(start_pos, end_pos, STYLE_THIN)

    # Draw negative wire
    canvas.draw_line(start_neg, end_neg, STYLE_THIN)

    # Draw pair label at midpoint
    mid_x = (start_pos.x + end_pos.x) / 2
    mid_y = (start_pos.y + end_pos.y) / 2
    canvas.draw_text(
        Point(mid_x, mid_y - 3),
        f"PR{pair_number}",
        DrawingStyle(font_size=3),
        anchor="middle"
    )
