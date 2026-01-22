"""PDF renderer for DCS interconnection diagrams."""

import io
import os
from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path

from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.units import mm

from .primitives import SVGCanvas, Point, DrawingStyle, STYLE_NORMAL
from .layout import PageLayout, LayoutCalculator
from .components import (
    draw_instrument_row,
    draw_junction_box,
    draw_multipair_cable,
    draw_marshalling_cabinet,
    draw_title_block,
    TitleBlockConfig,
)
from ..models import (
    Instrument,
    TerminalAllocation,
    DrawingSheet,
    DrawingMetadata,
)


class PDFRenderer:
    """Renders interconnection diagrams to PDF using ReportLab directly."""

    def __init__(self, layout: Optional[PageLayout] = None):
        """
        Initialize the PDF renderer.

        Args:
            layout: Optional page layout configuration
        """
        self.layout = layout or PageLayout()
        self.calculator = LayoutCalculator(self.layout)

    def render_sheet(
        self,
        sheet: DrawingSheet,
        output_path: str
    ):
        """
        Render a single drawing sheet to PDF.

        Args:
            sheet: DrawingSheet object
            output_path: Output file path
        """
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Create PDF canvas
        c = pdf_canvas.Canvas(output_path, pagesize=landscape(A3))

        # Draw all components directly to PDF
        self._draw_sheet_content_pdf(c, sheet)

        c.save()

    def render_multiple_sheets(
        self,
        sheets: List[DrawingSheet],
        output_path: str
    ):
        """
        Render multiple sheets to a single PDF.

        Args:
            sheets: List of DrawingSheet objects
            output_path: Output file path
        """
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Create PDF with multiple pages
        c = pdf_canvas.Canvas(output_path, pagesize=landscape(A3))

        for sheet in sheets:
            self._draw_sheet_content_pdf(c, sheet)
            c.showPage()

        c.save()

    def _draw_sheet_content_pdf(self, c: pdf_canvas.Canvas, sheet: DrawingSheet):
        """Draw all content for a sheet directly to PDF canvas."""
        # Get page dimensions
        page_width, page_height = landscape(A3)

        # Draw border
        self._draw_border_pdf(c, page_height)

        # Draw zone headers
        self._draw_zone_headers_pdf(c, page_height)

        # Draw instruments
        self._draw_instruments_pdf(c, sheet.instruments, page_height)

        # Draw junction box info
        if sheet.junction_box:
            self._draw_jb_info_pdf(c, sheet, page_height)

        # Draw multipair cable info
        if sheet.multipair_cable:
            self._draw_cable_info_pdf(c, sheet.multipair_cable, page_height)

        # Draw cabinet info
        if sheet.marshalling_cabinet:
            self._draw_cabinet_info_pdf(c, sheet, page_height)

        # Draw notes
        self._draw_notes_pdf(c, sheet.notes, page_height)

        # Draw title block
        self._draw_title_block_pdf(c, sheet.metadata, sheet.sheet_number, page_height)

    def _draw_border_pdf(self, c: pdf_canvas.Canvas, page_height: float):
        """Draw the drawing border."""
        x = self.layout.margin_left * mm
        y = page_height - self.layout.margin_top * mm - self.layout.drawing_height * mm
        width = self.layout.drawing_width * mm
        height = self.layout.drawing_height * mm

        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(0.5)
        c.rect(x, y, width, height)

    def _draw_zone_headers_pdf(self, c: pdf_canvas.Canvas, page_height: float):
        """Draw zone header labels."""
        c.setFont("Helvetica-Bold", 8)

        for zone_name, zone_config in self.layout.zones.items():
            x = self.layout.get_zone_x(zone_name)
            width = self.layout.get_zone_width(zone_name)

            # Draw header text
            header_lines = zone_config.header.split("\n")
            y_offset = 15

            for line in header_lines:
                text_x = (x + width/2) * mm
                text_y = page_height - (self.layout.margin_top + y_offset) * mm

                c.drawCentredString(text_x, text_y, line)
                y_offset += 8

            # Draw vertical divider line
            if zone_name != "zone5_notes":
                next_x = (x + width) * mm
                c.line(
                    next_x,
                    page_height - self.layout.margin_top * mm,
                    next_x,
                    page_height - (self.layout.margin_top + self.layout.drawing_height) * mm
                )

    def _draw_instruments_pdf(
        self,
        c: pdf_canvas.Canvas,
        instruments: List[Instrument],
        page_height: float
    ):
        """Draw instrument list."""
        c.setFont("Helvetica", 7)

        zone_x = self.layout.get_zone_x("zone1_instrument")
        start_y = self.layout.margin_top + 30

        for i, inst in enumerate(instruments):
            x = (zone_x + 5) * mm
            y = page_height - (start_y + i * self.layout.row_height) * mm

            # Draw instrument box
            box_width = 50 * mm
            box_height = 8 * mm
            c.rect(x, y - box_height/2, box_width, box_height)

            # Draw tag number
            c.drawString(x + 2*mm, y - 2*mm, inst.tag_number)

            # Draw connection lines
            conn_x = x + box_width
            c.line(conn_x, y, conn_x + 10*mm, y)

            # Draw + and - labels
            c.setFont("Helvetica", 5)
            c.drawString(conn_x + 12*mm, y + 1*mm, "+ WH")
            c.drawString(conn_x + 12*mm, y - 4*mm, "- BK")
            c.setFont("Helvetica", 7)

    def _draw_jb_info_pdf(
        self,
        c: pdf_canvas.Canvas,
        sheet: DrawingSheet,
        page_height: float
    ):
        """Draw junction box information."""
        zone_rect = self.layout.get_zone_rect("zone2_junction_box")
        x = (zone_rect["x"] + 10) * mm
        y = page_height - (zone_rect["y"] + 30) * mm

        jb = sheet.junction_box

        # Draw JB box
        box_width = 80 * mm
        box_height = min(200, 30 + len(sheet.instruments) * 12) * mm

        c.setStrokeColorRGB(0, 0, 0)
        c.rect(x, y - box_height, box_width, box_height)

        # Draw header
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x + box_width/2, y - 10*mm, jb.tag_number)

        # Draw horizontal line under header
        c.line(x, y - 15*mm, x + box_width, y - 15*mm)

        # Draw terminal allocations
        c.setFont("Helvetica", 6)
        alloc_y = y - 25*mm

        if jb.terminal_block:
            for alloc in jb.terminal_block.allocations[:12]:  # Limit to 12
                # Terminal labels
                c.drawString(x + 5*mm, alloc_y, f"{alloc.terminal_positive}")
                c.drawString(x + 15*mm, alloc_y, f"{alloc.terminal_negative}")

                # Instrument tag
                tag_display = alloc.instrument_tag
                if tag_display and len(tag_display) > 15:
                    tag_display = tag_display[-15:]
                c.drawString(x + 30*mm, alloc_y, tag_display or "SPARE")

                alloc_y -= 10*mm

    def _draw_cable_info_pdf(
        self,
        c: pdf_canvas.Canvas,
        cable,
        page_height: float
    ):
        """Draw multipair cable information."""
        zone_rect = self.layout.get_zone_rect("zone3_multipair")
        x = (zone_rect["x"] + 5) * mm
        y = page_height - (zone_rect["y"] + zone_rect["height"]/2) * mm

        # Draw cable box
        box_width = 35 * mm
        box_height = 30 * mm

        c.rect(x, y - box_height/2, box_width, box_height)

        # Draw cable info
        c.setFont("Helvetica-Bold", 7)
        short_tag = cable.tag_number.split("-")[-1] if "-" in cable.tag_number else cable.tag_number
        c.drawCentredString(x + box_width/2, y + 5*mm, short_tag)

        c.setFont("Helvetica", 6)
        c.drawCentredString(x + box_width/2, y - 2*mm, cable.specification)
        c.drawCentredString(x + box_width/2, y - 9*mm, f"({cable.used_pairs}/{cable.pair_count})")

        # Draw cable lines
        c.setLineWidth(1.5)
        c.line(x - 15*mm, y, x, y)
        c.line(x + box_width, y, x + box_width + 15*mm, y)
        c.setLineWidth(0.5)

    def _draw_cabinet_info_pdf(
        self,
        c: pdf_canvas.Canvas,
        sheet: DrawingSheet,
        page_height: float
    ):
        """Draw marshalling cabinet information."""
        zone_rect = self.layout.get_zone_rect("zone4_cabinet")
        x = (zone_rect["x"] + 5) * mm
        y = page_height - (zone_rect["y"] + 30) * mm

        cabinet = sheet.marshalling_cabinet

        # Draw cabinet box
        box_width = 100 * mm
        box_height = min(200, 40 + len(sheet.instruments) * 12) * mm

        c.rect(x, y - box_height, box_width, box_height)

        # Draw header
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x + box_width/2, y - 10*mm, cabinet.tag_number)

        # Draw TB tag
        if cabinet.terminal_blocks:
            tb = cabinet.terminal_blocks[0]
            c.setFont("Helvetica", 7)
            c.drawCentredString(x + box_width/2, y - 20*mm, tb.tag_number)

            # Draw horizontal lines
            c.line(x, y - 15*mm, x + box_width, y - 15*mm)
            c.line(x, y - 25*mm, x + box_width, y - 25*mm)

            # Draw DCS TAG header
            c.setFont("Helvetica", 5)
            c.drawString(x + box_width - 25*mm, y - 23*mm, "DCS TAG")

            # Draw terminal allocations
            c.setFont("Helvetica", 6)
            alloc_y = y - 35*mm

            for alloc in tb.allocations[:12]:  # Limit to 12
                pair_label = alloc.terminal_pair or f"PR{alloc.terminal_number}"
                c.drawString(x + 5*mm, alloc_y, pair_label)
                c.drawString(x + 20*mm, alloc_y, f"{alloc.terminal_positive}")
                c.drawString(x + 35*mm, alloc_y, f"{alloc.terminal_negative}")

                # DCS tag
                tag_display = alloc.dcs_tag or alloc.instrument_tag
                if tag_display and len(tag_display) > 12:
                    tag_display = tag_display[-12:]
                c.drawString(x + 55*mm, alloc_y, tag_display or "SPARE")

                alloc_y -= 10*mm

    def _draw_notes_pdf(
        self,
        c: pdf_canvas.Canvas,
        notes: List[str],
        page_height: float
    ):
        """Draw notes section."""
        zone_rect = self.layout.get_zone_rect("zone5_notes")
        x = (zone_rect["x"] + 5) * mm
        y = page_height - (zone_rect["y"] + 25) * mm

        c.setFont("Helvetica", 5)

        for note in notes:
            c.drawString(x, y, note)
            y -= 8*mm

    def _draw_title_block_pdf(
        self,
        c: pdf_canvas.Canvas,
        metadata: DrawingMetadata,
        sheet_number: int,
        page_height: float
    ):
        """Draw the title block."""
        tb_x = self.layout.margin_left * mm
        tb_y = self.layout.margin_bottom * mm
        tb_width = self.layout.drawing_width * mm
        tb_height = self.layout.title_block_height * mm

        # Draw title block border
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(1.0)
        c.rect(tb_x, tb_y, tb_width, tb_height)

        # Draw internal lines
        col1_x = tb_x + tb_width * 0.55
        col2_x = tb_x + tb_width * 0.75
        col3_x = tb_x + tb_width * 0.85

        c.setLineWidth(0.5)
        c.line(col1_x, tb_y, col1_x, tb_y + tb_height)
        c.line(col2_x, tb_y, col2_x, tb_y + tb_height)
        c.line(col3_x, tb_y, col3_x, tb_y + tb_height)

        # Horizontal divider
        mid_y = tb_y + tb_height/2
        c.line(col1_x, mid_y, tb_x + tb_width, mid_y)

        # Company name
        c.setFont("Helvetica-Bold", 8)
        c.drawString(tb_x + 5*mm, tb_y + tb_height - 12*mm, metadata.company)

        # Project name
        c.setFont("Helvetica", 6)
        project_lines = metadata.project_name.split("\n")
        proj_y = tb_y + tb_height - 12*mm
        for line in project_lines:
            c.drawString(col1_x + 5*mm, proj_y, line)
            proj_y -= 8*mm

        # Title
        c.setFont("Helvetica", 5)
        c.drawString(tb_x + 5*mm, mid_y + 8*mm, "TITLE:")
        c.setFont("Helvetica-Bold", 7)
        c.drawString(tb_x + 5*mm, mid_y - 5*mm, metadata.title)

        # Drawing number
        c.setFont("Helvetica", 5)
        c.drawString(col1_x + 5*mm, mid_y - 5*mm, "DWG NO.")
        c.setFont("Helvetica", 6)
        c.drawString(col1_x + 5*mm, mid_y - 15*mm, metadata.drawing_number)

        # Revision
        c.setFont("Helvetica", 5)
        c.drawString(col2_x + 5*mm, mid_y - 5*mm, "REV")
        c.setFont("Helvetica-Bold", 10)
        c.drawString(col2_x + 20*mm, mid_y - 8*mm, metadata.revision)

        # Sheet
        c.setFont("Helvetica", 5)
        c.drawString(col3_x + 5*mm, mid_y - 5*mm, "SHEET")
        c.setFont("Helvetica", 6)
        c.drawString(col3_x + 5*mm, mid_y - 15*mm, f"{sheet_number}")

        # Date
        c.setFont("Helvetica", 5)
        c.drawString(col3_x + 5*mm, tb_y + tb_height - 10*mm, "DATE")
        c.setFont("Helvetica", 6)
        c.drawString(col3_x + 5*mm, tb_y + tb_height - 18*mm, metadata.revision_date)


def render_interconnection_diagram(
    instruments: List[Instrument],
    jb_tag: str,
    cabinet_tag: str,
    multipair_cable_tag: str,
    tb_tag: str,
    output_path: str,
    drawing_number: str = "DWG-001",
    title: str = "Interconnection Diagram",
    spare_percent: float = 0.20,
):
    """
    Convenience function to render a complete interconnection diagram.

    Args:
        instruments: List of instruments
        jb_tag: Junction box tag
        cabinet_tag: Marshalling cabinet tag
        multipair_cable_tag: Multipair cable tag
        tb_tag: Terminal block tag
        output_path: Output PDF path
        drawing_number: Drawing number
        title: Drawing title
        spare_percent: Spare percentage for terminals
    """
    from ..engine import (
        allocate_all_terminals,
        size_cables_for_jb,
    )

    # Allocate terminals
    allocation_result = allocate_all_terminals(
        instruments=instruments,
        jb_tag=jb_tag,
        cabinet_tag=cabinet_tag,
        tb_tag=tb_tag,
        multipair_cable_tag=multipair_cable_tag,
        spare_percent=spare_percent,
    )

    # Size cables
    cable_result = size_cables_for_jb(
        instruments=instruments,
        jb_tag=jb_tag,
        cabinet_tag=cabinet_tag,
        multipair_cable_tag=multipair_cable_tag,
        spare_percent=spare_percent,
    )

    # Create drawing metadata
    metadata = DrawingMetadata(
        drawing_number=drawing_number,
        title=title,
    )

    # Create drawing sheet
    sheet = DrawingSheet(
        sheet_number=1,
        metadata=metadata,
        instruments=instruments,
        junction_box=allocation_result["junction_box"],
        multipair_cable=cable_result.multipair_cable,
        marshalling_cabinet=allocation_result["cabinet"],
        notes=[
            "1. ALL CABLES TO BE INSTALLED AS PER SPECIFICATION",
            "2. SPARE TERMINALS TO BE LEFT FOR FUTURE USE",
            "3. OVERALL SHIELD TO BE CONNECTED TO EARTH BAR",
        ]
    )

    # Render to PDF
    renderer = PDFRenderer()
    renderer.render_sheet(sheet, output_path)

    return output_path


def render_multi_jb_diagram(
    instruments: List[Instrument],
    base_jb_tag: str,
    cabinet_tag: str,
    base_multipair_cable_tag: str,
    base_tb_tag: str,
    output_path: str,
    drawing_number: str = "DWG-001",
    title: str = "Interconnection Diagram",
    spare_percent: float = 0.20,
    signal_category: str = None,
) -> dict:
    """
    Render interconnection diagrams, automatically splitting across multiple JBs if needed.

    For large instrument counts, this function automatically:
    1. Calculates the optimal number of JBs
    2. Distributes instruments evenly across JBs
    3. Generates a PDF for each JB (or merged multi-page PDF)

    Args:
        instruments: List of instruments
        base_jb_tag: Base junction box tag (suffixed with A, B, C for multiple)
        cabinet_tag: Marshalling cabinet tag
        base_multipair_cable_tag: Base multipair cable tag
        base_tb_tag: Base terminal block tag
        output_path: Output PDF path (for single JB) or base path (for multiple)
        drawing_number: Base drawing number
        title: Drawing title
        spare_percent: Spare percentage for terminals
        signal_category: "ANALOG" or "DIGITAL" (auto-detected if None)

    Returns:
        Dictionary with:
            - 'num_jbs': Number of JBs used
            - 'output_files': List of generated PDF file paths
            - 'plan': The JB allocation plan used
    """
    from ..engine import (
        allocate_all_terminals_auto,
        size_cables_for_jb,
        calculate_jb_allocation_plan,
        determine_signal_category,
    )

    # Determine signal category if not provided
    if signal_category is None:
        signal_category = determine_signal_category(instruments)

    # Calculate allocation plan
    plan = calculate_jb_allocation_plan(len(instruments), spare_percent)

    # Generate signal-specific notes
    if signal_category == "ANALOG":
        signal_notes = [
            "1. ANALOG SIGNALS (4-20mA) - USE ISP CABLES",
            "2. BRANCH: 1Px1.5mm² ISTP (Individually Shielded)",
            "3. MULTIPAIR: ISP+OS (Individual Shield + Overall)",
            "4. SHIELD GROUNDED AT DCS END ONLY",
            "5. SPARE TERMINALS TO BE LEFT FOR FUTURE USE",
        ]
    else:
        signal_notes = [
            "1. DIGITAL SIGNALS (24VDC) - USE OS CABLES",
            "2. BRANCH: 1Px1.0mm² OS (Overall Shielded)",
            "3. MULTIPAIR: OS (Overall Shield Only)",
            "4. SHIELD GROUNDED AT DCS END ONLY",
            "5. SPARE TERMINALS TO BE LEFT FOR FUTURE USE",
        ]

    # If single JB is enough, use simple rendering
    if plan.num_jbs_needed == 1:
        from ..engine import TagGenerator
        tag_gen = TagGenerator()

        # Use signal-category aware cable sizing
        from ..engine import allocate_all_terminals
        allocation_result = allocate_all_terminals(
            instruments=instruments,
            jb_tag=base_jb_tag,
            cabinet_tag=cabinet_tag,
            tb_tag=base_tb_tag,
            multipair_cable_tag=base_multipair_cable_tag,
            spare_percent=spare_percent,
        )

        cable_result = size_cables_for_jb(
            instruments=instruments,
            jb_tag=base_jb_tag,
            cabinet_tag=cabinet_tag,
            multipair_cable_tag=base_multipair_cable_tag,
            spare_percent=spare_percent,
            signal_category=signal_category,
        )

        metadata = DrawingMetadata(
            drawing_number=drawing_number,
            title=title,
        )

        sheet = DrawingSheet(
            sheet_number=1,
            metadata=metadata,
            instruments=instruments,
            junction_box=allocation_result["junction_box"],
            multipair_cable=cable_result.multipair_cable,
            marshalling_cabinet=allocation_result["cabinet"],
            notes=signal_notes,
        )

        renderer = PDFRenderer()
        renderer.render_sheet(sheet, output_path)

        return {
            'num_jbs': 1,
            'output_files': [output_path],
            'plan': plan,
            'jb_tags': [base_jb_tag],
        }

    # Auto-allocate across multiple JBs
    allocation = allocate_all_terminals_auto(
        instruments=instruments,
        base_jb_tag=base_jb_tag,
        cabinet_tag=cabinet_tag,
        base_tb_tag=base_tb_tag,
        base_multipair_cable_tag=base_multipair_cable_tag,
        spare_percent=spare_percent,
    )

    output_files = []
    jb_tags = []
    suffixes = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    # Prepare output path base
    base_path = Path(output_path)
    base_name = base_path.stem
    base_dir = base_path.parent

    # Generate a diagram for each JB
    start_idx = 0
    for jb_idx, jb in enumerate(allocation['junction_boxes']):
        # Get instruments for this JB
        inst_count = allocation['plan'].instruments_per_jb[jb_idx]
        end_idx = start_idx + inst_count
        jb_instruments = instruments[start_idx:end_idx]
        start_idx = end_idx

        # Generate tags for this JB
        suffix = suffixes[jb_idx] if jb_idx < len(suffixes) else str(jb_idx + 1)
        jb_tag = jb.tag_number
        jb_tags.append(jb_tag)

        multipair_cable_tag = f"{base_multipair_cable_tag}{suffix}"
        tb_tag = f"{base_tb_tag}{suffix}"
        jb_drawing_number = f"{drawing_number}-{suffix}"
        jb_title = f"{title} - JB {suffix}"

        # Output path for this JB
        jb_output_path = base_dir / f"{base_name}_{suffix}.pdf"

        # Size cables for this JB with signal category
        cable_result = size_cables_for_jb(
            instruments=jb_instruments,
            jb_tag=jb_tag,
            cabinet_tag=cabinet_tag,
            multipair_cable_tag=multipair_cable_tag,
            spare_percent=spare_percent,
            signal_category=signal_category,
        )

        # Create drawing metadata
        metadata = DrawingMetadata(
            drawing_number=jb_drawing_number,
            title=jb_title,
        )

        # Add JB-specific note
        jb_notes = signal_notes.copy()
        jb_notes.append(f"6. JB {suffix} OF {allocation['num_jbs']} ({inst_count} INSTRUMENTS)")

        # Create drawing sheet
        sheet = DrawingSheet(
            sheet_number=jb_idx + 1,
            metadata=metadata,
            instruments=jb_instruments,
            junction_box=jb,
            multipair_cable=cable_result.multipair_cable,
            marshalling_cabinet=allocation['cabinet'],
            notes=jb_notes,
        )

        # Render to PDF
        renderer = PDFRenderer()
        renderer.render_sheet(sheet, str(jb_output_path))
        output_files.append(str(jb_output_path))

    return {
        'num_jbs': allocation['num_jbs'],
        'output_files': output_files,
        'plan': allocation['plan'],
        'jb_tags': jb_tags,
        'instruments_per_jb': allocation['plan'].instruments_per_jb,
    }
