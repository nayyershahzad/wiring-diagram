"""Title Block drawing component."""

from typing import Optional
from dataclasses import dataclass
from datetime import date

from ..primitives import SVGCanvas, Point, DrawingStyle, STYLE_NORMAL, STYLE_THIN, STYLE_THICK


@dataclass
class TitleBlockConfig:
    """Configuration for title block."""
    width: float = 400  # Full width minus margins
    height: float = 45
    company: str = "CHINA PETROLEUM ENGINEERING & CONSTRUCTION CORP."
    project_name: str = "EARLY POWER PLANT\nRUMAILA OIL FIELD"
    contract: str = "100478"


def draw_title_block(
    canvas: SVGCanvas,
    position: Point,
    drawing_number: str,
    title: str,
    revision: str = "0",
    drawn_by: str = "",
    checked_by: str = "",
    approved_by: str = "",
    date_str: str = None,
    sheet_info: str = "",
    config: Optional[TitleBlockConfig] = None
) -> dict:
    """
    Draw a standard title block.

    Layout:
    ┌──────────────────────────────────────────────────────────────────────────┐
    │ COMPANY NAME                          │ PROJECT      │ DRAWN  │ DATE    │
    │                                       │              │ CHK    │         │
    ├───────────────────────────────────────┤              │ APP    │         │
    │ TITLE                                 ├──────────────┼────────┼─────────┤
    │                                       │ DWG NO.      │ REV    │ SHEET   │
    └──────────────────────────────────────────────────────────────────────────┘

    Args:
        canvas: SVG canvas
        position: Top-left position
        drawing_number: Drawing number
        title: Drawing title
        revision: Revision number
        drawn_by: Drawn by name
        checked_by: Checked by name
        approved_by: Approved by name
        date_str: Date string
        sheet_info: Sheet information (e.g., "1 OF 3")
        config: Optional configuration

    Returns:
        Dictionary with dimensions
    """
    cfg = config or TitleBlockConfig()

    if date_str is None:
        date_str = date.today().strftime("%Y-%m-%d")

    # Main border
    canvas.draw_rect(position, cfg.width, cfg.height, STYLE_THICK)

    # Vertical dividers
    col1_width = cfg.width * 0.55  # Company/Title
    col2_width = cfg.width * 0.20  # Project/Drawing No
    col3_width = cfg.width * 0.10  # Signatures
    col4_width = cfg.width * 0.15  # Date/Rev/Sheet

    x1 = position.x + col1_width
    x2 = x1 + col2_width
    x3 = x2 + col3_width

    # Vertical lines
    canvas.draw_vertical_line(Point(x1, position.y), cfg.height, STYLE_NORMAL)
    canvas.draw_vertical_line(Point(x2, position.y), cfg.height, STYLE_NORMAL)
    canvas.draw_vertical_line(Point(x3, position.y), cfg.height, STYLE_NORMAL)

    # Horizontal dividers
    row1_height = cfg.height * 0.5
    row1_y = position.y + row1_height

    # Horizontal line (partial - only in right columns)
    canvas.draw_horizontal_line(Point(x1, row1_y), cfg.width - col1_width, STYLE_NORMAL)

    # Additional horizontal lines for signature rows
    sig_row_height = row1_height / 3
    for i in range(1, 3):
        y = position.y + sig_row_height * i
        canvas.draw_horizontal_line(Point(x2, y), col3_width + col4_width, STYLE_THIN)

    # Text content
    text_style = DrawingStyle(font_size=6)
    small_style = DrawingStyle(font_size=4)
    label_style = DrawingStyle(font_size=3)

    # Company name
    canvas.draw_text(
        Point(position.x + 5, position.y + 8),
        cfg.company,
        text_style
    )

    # Project name
    project_lines = cfg.project_name.split("\n")
    project_y = position.y + 8
    for line in project_lines:
        canvas.draw_text(
            Point(x1 + 5, project_y),
            line,
            small_style
        )
        project_y += 6

    # Title (left side, bottom half)
    canvas.draw_text(
        Point(position.x + 5, row1_y + 8),
        "TITLE:",
        label_style
    )
    canvas.draw_text(
        Point(position.x + 5, row1_y + 15),
        title,
        text_style
    )

    # Signature labels and fields
    sig_labels = [("DRAWN", drawn_by), ("CHK", checked_by), ("APP", approved_by)]
    sig_y = position.y + 5
    for label, value in sig_labels:
        canvas.draw_text(Point(x2 + 3, sig_y), label, label_style)
        canvas.draw_text(Point(x2 + 15, sig_y), value, small_style)
        sig_y += sig_row_height

    # Date
    canvas.draw_text(Point(x3 + 3, position.y + 5), "DATE", label_style)
    canvas.draw_text(Point(x3 + 3, position.y + 12), date_str, small_style)

    # Drawing number
    canvas.draw_text(Point(x1 + 5, row1_y + 5), "DWG NO.", label_style)
    canvas.draw_text(Point(x1 + 5, row1_y + 12), drawing_number, small_style)

    # Revision
    canvas.draw_text(Point(x2 + 3, row1_y + 5), "REV", label_style)
    canvas.draw_text(Point(x2 + 15, row1_y + 5), revision, text_style)

    # Sheet info
    canvas.draw_text(Point(x3 + 3, row1_y + 5), "SHEET", label_style)
    canvas.draw_text(Point(x3 + 3, row1_y + 12), sheet_info, small_style)

    return {
        "width": cfg.width,
        "height": cfg.height,
        "bottom_y": position.y + cfg.height,
    }


def draw_revision_block(
    canvas: SVGCanvas,
    position: Point,
    revisions: list,
    width: float = 100,
    row_height: float = 8
) -> dict:
    """
    Draw a revision history block.

    Args:
        canvas: SVG canvas
        position: Top-left position
        revisions: List of revision dictionaries with 'rev', 'date', 'description'
        width: Block width
        row_height: Height per revision row

    Returns:
        Dictionary with dimensions
    """
    header_height = 10
    total_height = header_height + len(revisions) * row_height

    # Border
    canvas.draw_rect(position, width, total_height, STYLE_NORMAL)

    # Header
    canvas.draw_horizontal_line(
        Point(position.x, position.y + header_height),
        width,
        STYLE_NORMAL
    )
    canvas.draw_text(
        Point(position.x + width/2, position.y + 7),
        "REVISION HISTORY",
        DrawingStyle(font_size=5),
        anchor="middle"
    )

    # Column dividers
    col_widths = [15, 25, 60]  # REV, DATE, DESCRIPTION
    x = position.x
    for w in col_widths[:-1]:
        x += w
        canvas.draw_vertical_line(Point(x, position.y), total_height, STYLE_THIN)

    # Column headers
    headers = ["REV", "DATE", "DESCRIPTION"]
    x = position.x + 2
    for header, w in zip(headers, col_widths):
        canvas.draw_text(
            Point(x, position.y + header_height + 5),
            header,
            DrawingStyle(font_size=3)
        )
        x += w

    # Revision entries
    y = position.y + header_height + row_height
    for rev in revisions:
        x = position.x + 2
        canvas.draw_text(Point(x, y), str(rev.get('rev', '')), DrawingStyle(font_size=4))
        x += col_widths[0]
        canvas.draw_text(Point(x, y), str(rev.get('date', '')), DrawingStyle(font_size=4))
        x += col_widths[1]
        canvas.draw_text(Point(x, y), str(rev.get('description', '')), DrawingStyle(font_size=4))
        y += row_height

    return {
        "width": width,
        "height": total_height,
    }
