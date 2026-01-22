"""Processing engine for DCS interconnection diagram generator."""

from .classifier import (
    JBType,
    classify_instrument,
    classify_jb_type,
    get_jb_tag_prefix,
    is_input_signal,
    is_output_signal,
    get_io_type_code,
    group_instruments_by_jb_type,
    suggest_jb_count,
)

from .cable_sizer import (
    CableSizingError,
    CableSizingResult,
    get_branch_cable_spec,
    create_branch_cable,
    calculate_multipair_size,
    get_multipair_specification,
    create_multipair_cable,
    size_cables_for_jb,
    calculate_multiple_multipairs,
    determine_signal_category,
)

from .terminal_allocator import (
    TerminalAllocationError,
    AllocationResult,
    JBSize,
    JBAllocationPlan,
    MultiJBAllocationResult,
    SignalTypeAllocationResult,
    ANALOG_SIGNAL_TYPES,
    DIGITAL_SIGNAL_TYPES,
    calculate_terminals_needed,
    calculate_jb_allocation_plan,
    suggest_jb_configuration,
    allocate_jb_terminals,
    allocate_cabinet_terminals,
    create_junction_box,
    create_marshalling_cabinet,
    allocate_all_terminals,
    allocate_multiple_jbs,
    allocate_all_terminals_auto,
    separate_instruments_by_signal_type,
    allocate_by_signal_type,
    get_signal_type_summary,
)

from .tag_generator import (
    TagConfig,
    TagGenerator,
    generate_jb_tag,
    generate_multipair_cable_tag,
    generate_tb_tag,
    parse_instrument_tag,
    parse_jb_tag,
)

from .io_allocator import (
    IOAllocator,
    IOAllocationError,
    calculate_io_allocation,
    SignalCount,
    SystemAllocation,
)

from .io_card_database import (
    IOCardDatabase,
    VendorSpec,
    get_io_card_database,
)

__all__ = [
    # Classifier
    "JBType",
    "classify_instrument",
    "classify_jb_type",
    "get_jb_tag_prefix",
    "is_input_signal",
    "is_output_signal",
    "get_io_type_code",
    "group_instruments_by_jb_type",
    "suggest_jb_count",
    # Cable Sizer
    "CableSizingError",
    "CableSizingResult",
    "get_branch_cable_spec",
    "create_branch_cable",
    "calculate_multipair_size",
    "get_multipair_specification",
    "create_multipair_cable",
    "size_cables_for_jb",
    "calculate_multiple_multipairs",
    "determine_signal_category",
    # Terminal Allocator
    "TerminalAllocationError",
    "AllocationResult",
    "JBSize",
    "JBAllocationPlan",
    "MultiJBAllocationResult",
    "SignalTypeAllocationResult",
    "ANALOG_SIGNAL_TYPES",
    "DIGITAL_SIGNAL_TYPES",
    "calculate_terminals_needed",
    "calculate_jb_allocation_plan",
    "suggest_jb_configuration",
    "allocate_jb_terminals",
    "allocate_cabinet_terminals",
    "create_junction_box",
    "create_marshalling_cabinet",
    "allocate_all_terminals",
    "allocate_multiple_jbs",
    "allocate_all_terminals_auto",
    "separate_instruments_by_signal_type",
    "allocate_by_signal_type",
    "get_signal_type_summary",
    # Tag Generator
    "TagConfig",
    "TagGenerator",
    "generate_jb_tag",
    "generate_multipair_cable_tag",
    "generate_tb_tag",
    "parse_instrument_tag",
    "parse_jb_tag",
    # I/O Card Allocation
    "IOAllocator",
    "IOAllocationError",
    "calculate_io_allocation",
    "SignalCount",
    "SystemAllocation",
    "IOCardDatabase",
    "VendorSpec",
    "get_io_card_database",
]
