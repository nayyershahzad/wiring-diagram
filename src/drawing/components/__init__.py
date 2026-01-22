"""Drawing components for DCS interconnection diagrams."""

from .instrument import (
    InstrumentSymbolConfig,
    draw_instrument_symbol,
    draw_instrument_row,
)

from .junction_box import (
    JBDrawingConfig,
    draw_junction_box,
    draw_jb_compact,
)

from .cable import (
    CableDrawingConfig,
    draw_multipair_cable,
    draw_cable_run,
    draw_branch_cable,
    draw_wire_pair,
)

from .marshalling import (
    CabinetDrawingConfig,
    draw_marshalling_cabinet,
    draw_cabinet_compact,
)

from .title_block import (
    TitleBlockConfig,
    draw_title_block,
    draw_revision_block,
)

__all__ = [
    # Instrument
    "InstrumentSymbolConfig",
    "draw_instrument_symbol",
    "draw_instrument_row",
    # Junction Box
    "JBDrawingConfig",
    "draw_junction_box",
    "draw_jb_compact",
    # Cable
    "CableDrawingConfig",
    "draw_multipair_cable",
    "draw_cable_run",
    "draw_branch_cable",
    "draw_wire_pair",
    # Marshalling Cabinet
    "CabinetDrawingConfig",
    "draw_marshalling_cabinet",
    "draw_cabinet_compact",
    # Title Block
    "TitleBlockConfig",
    "draw_title_block",
    "draw_revision_block",
]
