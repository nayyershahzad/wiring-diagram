"""I/O Allocation Report generator for PDF output."""

from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import Table, TableStyle

from ..models.io_card import IOAllocationResult, IOCard, ControlSystem


@dataclass
class ReportConfig:
    """Configuration for I/O allocation report."""
    project_name: str = "I/O Card Allocation Report"
    project_number: str = ""
    vendor: str = "Yokogawa"
    revision: str = "A"
    prepared_by: str = ""
    checked_by: str = ""


class IOAllocationReportGenerator:
    """Generates PDF reports for I/O card allocations."""

    def __init__(self, config: Optional[ReportConfig] = None):
        """Initialize the report generator."""
        self.config = config or ReportConfig()

    def generate_pdf(
        self,
        result: IOAllocationResult,
        output_path: str
    ):
        """
        Generate PDF report from allocation result.

        Args:
            result: IOAllocationResult from allocator
            output_path: Output PDF file path
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        c = pdf_canvas.Canvas(output_path, pagesize=A4)
        width, height = A4

        # Draw header
        y_pos = self._draw_header(c, width, height)

        # Draw summary section
        y_pos = self._draw_summary(c, result, y_pos, width)

        # Draw DCS allocation
        if result.dcs_cards:
            y_pos = self._draw_system_allocation(
                c, "DCS (CENTUM VP)", result.dcs_summary,
                result.dcs_cards, y_pos, width
            )

        # Check if we need a new page
        if y_pos < 200:
            c.showPage()
            y_pos = height - 50

        # Draw SIS allocation
        if result.sis_cards:
            y_pos = self._draw_system_allocation(
                c, "SIS (ProSafe-RS)", result.sis_summary,
                result.sis_cards, y_pos, width
            )

        # Check if we need a new page
        if y_pos < 200 and result.rtu_cards:
            c.showPage()
            y_pos = height - 50

        # Draw RTU allocation (if any)
        if result.rtu_cards:
            y_pos = self._draw_system_allocation(
                c, "RTU (STARDOM)", result.rtu_summary,
                result.rtu_cards, y_pos, width
            )

        # Draw segregation rules
        y_pos = self._draw_segregation_rules(c, result, y_pos, width)

        # Draw detailed channel assignments (on new pages)
        if result.dcs_cards:
            c.showPage()
            y_pos = height - 50
            y_pos = self._draw_channel_assignments(
                c, "DCS (CENTUM VP)", result.dcs_cards, y_pos, width, height
            )

        if result.sis_cards:
            c.showPage()
            y_pos = height - 50
            y_pos = self._draw_channel_assignments(
                c, "SIS (ProSafe-RS)", result.sis_cards, y_pos, width, height
            )

        if result.rtu_cards:
            c.showPage()
            y_pos = height - 50
            y_pos = self._draw_channel_assignments(
                c, "RTU (STARDOM)", result.rtu_cards, y_pos, width, height
            )

        # Draw footer
        self._draw_footer(c, width)

        c.save()

    def _draw_header(self, c: pdf_canvas.Canvas, width: float, height: float) -> float:
        """Draw report header."""
        y_pos = height - 40

        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(width/2, y_pos, "I/O CARD ALLOCATION REPORT")
        y_pos -= 25

        c.setFont("Helvetica", 11)
        if self.config.project_name:
            c.drawCentredString(width/2, y_pos, f"Project: {self.config.project_name}")
            y_pos -= 15

        if self.config.project_number:
            c.drawCentredString(width/2, y_pos, f"Contract: {self.config.project_number}")
            y_pos -= 15

        c.drawCentredString(width/2, y_pos, f"Vendor: {self.config.vendor}")
        y_pos -= 20

        # Draw separator line
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.5)
        c.line(50, y_pos, width - 50, y_pos)
        y_pos -= 20

        return y_pos

    def _draw_summary(
        self,
        c: pdf_canvas.Canvas,
        result: IOAllocationResult,
        y_pos: float,
        width: float
    ) -> float:
        """Draw summary section."""
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_pos, "ALLOCATION SUMMARY")
        y_pos -= 25

        # Calculate totals
        total_ai = result.dcs_summary.get('AI', 0) + result.sis_summary.get('AI', 0) + result.rtu_summary.get('AI', 0)
        total_ao = result.dcs_summary.get('AO', 0) + result.sis_summary.get('AO', 0) + result.rtu_summary.get('AO', 0)
        total_di = result.dcs_summary.get('DI', 0) + result.sis_summary.get('DI', 0) + result.rtu_summary.get('DI', 0)
        total_do = result.dcs_summary.get('DO', 0) + result.sis_summary.get('DO', 0) + result.rtu_summary.get('DO', 0)

        # Summary table
        data = [
            ["System", "AI", "AO", "DI", "DO", "Total Signals", "Cards", "Spare %"],
            [
                "DCS",
                str(result.dcs_summary.get('AI', 0)),
                str(result.dcs_summary.get('AO', 0)),
                str(result.dcs_summary.get('DI', 0)),
                str(result.dcs_summary.get('DO', 0)),
                str(sum(result.dcs_summary.values())),
                str(len(result.dcs_cards)),
                f"{result.spare_percent_target:.0f}%"
            ],
            [
                "SIS",
                str(result.sis_summary.get('AI', 0)),
                str(result.sis_summary.get('AO', 0)),
                str(result.sis_summary.get('DI', 0)),
                str(result.sis_summary.get('DO', 0)),
                str(sum(result.sis_summary.values())),
                str(len(result.sis_cards)),
                f"{result.spare_percent_target:.0f}%"
            ],
            [
                "RTU",
                str(result.rtu_summary.get('AI', 0)),
                str(result.rtu_summary.get('AO', 0)),
                str(result.rtu_summary.get('DI', 0)),
                str(result.rtu_summary.get('DO', 0)),
                str(sum(result.rtu_summary.values())),
                str(len(result.rtu_cards)),
                f"{result.spare_percent_target:.0f}%"
            ],
            [
                "TOTAL",
                str(total_ai),
                str(total_ao),
                str(total_di),
                str(total_do),
                str(total_ai + total_ao + total_di + total_do),
                str(result.total_cards),
                ""
            ],
        ]

        table = Table(data, colWidths=[60, 45, 45, 45, 45, 75, 50, 55])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.3)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.85, 0.85, 0.85)),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))

        table_width, table_height = table.wrap(width, 200)
        table.drawOn(c, 50, y_pos - table_height)

        return y_pos - table_height - 30

    def _draw_system_allocation(
        self,
        c: pdf_canvas.Canvas,
        system_name: str,
        summary: dict,
        cards: List[IOCard],
        y_pos: float,
        width: float
    ) -> float:
        """Draw allocation details for a system."""
        if not cards:
            return y_pos

        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, system_name)
        y_pos -= 20

        # Card details table
        data = [["#", "Module", "Type", "Channels", "Used", "Spare", "Util %"]]

        for card in cards:
            data.append([
                str(card.card_number),
                card.module.model,
                card.module.io_type.value,
                str(card.total_channels),
                str(card.used_channels),
                str(card.spare_channels),
                f"{card.utilization_percent:.0f}%"
            ])

        table = Table(data, colWidths=[30, 100, 40, 60, 50, 50, 50])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.7, 0.7, 0.8)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))

        table_width, table_height = table.wrap(width, 500)
        table.drawOn(c, 50, y_pos - table_height)

        return y_pos - table_height - 25

    def _draw_channel_assignments(
        self,
        c: pdf_canvas.Canvas,
        system_name: str,
        cards: List[IOCard],
        y_pos: float,
        width: float,
        height: float
    ) -> float:
        """Draw detailed channel assignments for each card."""
        if not cards:
            return y_pos

        # Check if we need a new page
        if y_pos < 150:
            c.showPage()
            y_pos = height - 50

        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, f"{system_name} - Channel Assignments")
        y_pos -= 20

        for card in cards:
            # Check if we need a new page
            if y_pos < 200:
                c.showPage()
                y_pos = height - 50
                c.setFont("Helvetica-Bold", 12)
                c.drawString(50, y_pos, f"{system_name} - Channel Assignments (continued)")
                y_pos -= 20

            # Card header
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y_pos, f"Card #{card.card_number}: {card.module.model} ({card.module.io_type.value})")
            y_pos -= 15

            # Build channel data
            data = [["CH", "Instrument Tag", "Type", "Service", "Status"]]
            for ch_num in sorted(card.channel_assignments.keys()):
                ch_data = card.channel_assignments[ch_num]
                tag = ch_data.get('tag', 'SPARE')
                inst_type = ch_data.get('type', '')
                service = ch_data.get('service', '')[:30]  # Truncate service
                status = ch_data.get('status', 'SPARE')
                data.append([str(ch_num), tag, inst_type, service, status])

            table = Table(data, colWidths=[30, 120, 50, 180, 50])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.7, 0.75, 0.85)),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (-1, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.gray),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
            ]))

            # Highlight SPARE rows
            for i, row in enumerate(data[1:], start=1):
                if row[-1] == 'SPARE':
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, i), (-1, i), colors.Color(1.0, 0.95, 0.85)),
                        ('TEXTCOLOR', (1, i), (1, i), colors.Color(0.8, 0.5, 0.0)),
                    ]))

            table_width, table_height = table.wrap(width - 100, 500)
            table.drawOn(c, 50, y_pos - table_height)

            y_pos = y_pos - table_height - 15

        return y_pos - 10

    def _draw_segregation_rules(
        self,
        c: pdf_canvas.Canvas,
        result: IOAllocationResult,
        y_pos: float,
        width: float
    ) -> float:
        """Draw segregation rules section."""
        if y_pos < 150:
            c.showPage()
            y_pos = A4[1] - 50

        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, "SEGREGATION RULES APPLIED")
        y_pos -= 20

        c.setFont("Helvetica", 9)
        for rule in result.segregation_rules_applied:
            c.drawString(60, y_pos, f"• {rule}")
            y_pos -= 14

        return y_pos - 10

    def _draw_footer(self, c: pdf_canvas.Canvas, width: float):
        """Draw report footer."""
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.Color(0.5, 0.5, 0.5))

        footer_y = 30
        c.drawString(50, footer_y, f"Generated by U2C2.ai I/O Allocation Tool")
        c.drawRightString(width - 50, footer_y, f"Rev: {self.config.revision}")

        if self.config.prepared_by:
            c.drawString(50, footer_y - 12, f"Prepared by: {self.config.prepared_by}")
        if self.config.checked_by:
            c.drawString(250, footer_y - 12, f"Checked by: {self.config.checked_by}")


def generate_io_allocation_report(
    result: IOAllocationResult,
    output_path: str,
    config: Optional[ReportConfig] = None
):
    """
    Convenience function to generate I/O allocation report.

    Args:
        result: IOAllocationResult from allocator
        output_path: Output PDF file path
        config: Optional report configuration
    """
    generator = IOAllocationReportGenerator(config)
    generator.generate_pdf(result, output_path)
