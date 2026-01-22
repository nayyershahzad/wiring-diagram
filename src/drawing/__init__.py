"""Drawing module for DCS interconnection diagram generator."""

from .primitives import (
    Point,
    DrawingStyle,
    SVGCanvas,
    STYLE_NORMAL,
    STYLE_THIN,
    STYLE_THICK,
    STYLE_BORDER,
    mm_to_px,
    px_to_mm,
)

from .layout import (
    PageLayout,
    LayoutCalculator,
    ZoneConfig,
    create_default_layout,
    calculate_wire_routes,
)

from .renderer import (
    PDFRenderer,
    render_interconnection_diagram,
    render_multi_jb_diagram,
)

from .components import (
    InstrumentSymbolConfig,
    draw_instrument_symbol,
    draw_instrument_row,
    JBDrawingConfig,
    draw_junction_box,
    draw_jb_compact,
    CableDrawingConfig,
    draw_multipair_cable,
    draw_cable_run,
    draw_branch_cable,
    draw_wire_pair,
    CabinetDrawingConfig,
    draw_marshalling_cabinet,
    draw_cabinet_compact,
    TitleBlockConfig,
    draw_title_block,
    draw_revision_block,
)

__all__ = [
    # Primitives
    "Point",
    "DrawingStyle",
    "SVGCanvas",
    "STYLE_NORMAL",
    "STYLE_THIN",
    "STYLE_THICK",
    "STYLE_BORDER",
    "mm_to_px",
    "px_to_mm",
    # Layout
    "PageLayout",
    "LayoutCalculator",
    "ZoneConfig",
    "create_default_layout",
    "calculate_wire_routes",
    # Renderer
    "PDFRenderer",
    "render_interconnection_diagram",
    "render_multi_jb_diagram",
    # Components
    "InstrumentSymbolConfig",
    "draw_instrument_symbol",
    "draw_instrument_row",
    "JBDrawingConfig",
    "draw_junction_box",
    "draw_jb_compact",
    "CableDrawingConfig",
    "draw_multipair_cable",
    "draw_cable_run",
    "draw_branch_cable",
    "draw_wire_pair",
    "CabinetDrawingConfig",
    "draw_marshalling_cabinet",
    "draw_cabinet_compact",
    "TitleBlockConfig",
    "draw_title_block",
    "draw_revision_block",
]
