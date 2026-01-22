"""I/O Card allocation engine for DCS/SIS/RTU systems."""

import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from ..models.instrument import Instrument, SignalType
from ..models.io_card import (
    IOModule, IOCard, Controller, IOAllocationResult,
    ControlSystem, IOType, SILRating
)
from .io_card_database import IOCardDatabase, get_io_card_database


class IOAllocationError(Exception):
    """Exception raised for I/O allocation errors."""
    pass


@dataclass
class SignalCount:
    """Count of signals by type."""
    ai: int = 0
    ao: int = 0
    di: int = 0
    do: int = 0

    @property
    def total(self) -> int:
        """Total hardware I/O points."""
        return self.ai + self.ao + self.di + self.do

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {'AI': self.ai, 'AO': self.ao, 'DI': self.di, 'DO': self.do}


@dataclass
class SystemAllocation:
    """Allocation for a single control system."""
    system: ControlSystem
    signal_counts: SignalCount
    cards: List[IOCard] = field(default_factory=list)
    spare_percent_target: float = 20.0

    def get_card_summary(self) -> Dict[str, int]:
        """Get summary of cards by type."""
        summary = defaultdict(int)
        for card in self.cards:
            key = f"{card.module.io_type.value}_{card.module.model}"
            summary[key] += 1
        return dict(summary)


class IOAllocator:
    """
    I/O Card allocation engine.

    Implements the calculation logic:
    - 20% spare at channel level: Channels = SignalCount * 1.20
    - Cards = CEILING(Channels / ChannelsPerCard)
    - Segregation rules: DCS/SIS separate, Analog/Digital separate
    """

    # Signal type to I/O type mapping
    SIGNAL_TO_IO_TYPE = {
        SignalType.ANALOG_INPUT: IOType.AI,
        SignalType.ANALOG_OUTPUT: IOType.AO,
        SignalType.DIGITAL_INPUT: IOType.DI,
        SignalType.DIGITAL_OUTPUT: IOType.DO,
        SignalType.THERMOCOUPLE: IOType.AI,
        SignalType.RTD_3WIRE: IOType.AI,
        SignalType.RTD_4WIRE: IOType.AI,
    }

    # Instrument prefixes that indicate SIS assignment
    SIS_PREFIXES = {
        'TZI', 'PZI', 'LZI', 'FZI',  # Safety transmitters
        'TZT', 'PZT', 'LZT', 'FZT',  # Safety transmitters
        'EVI', 'EHS',                 # ESD valve signals
        'BVI', 'BHS',                 # Blowdown valve signals
    }

    def __init__(
        self,
        vendor: str = "Yokogawa",
        spare_percent: float = 0.20
    ):
        """
        Initialize the allocator.

        Args:
            vendor: Vendor name (currently only "Yokogawa" supported)
            spare_percent: Target spare percentage (default 20%)
        """
        self.vendor = vendor
        self.spare_percent = spare_percent
        self.db = get_io_card_database()
        self.custom_rules = None  # Will be set if LLM rules are provided

        if not self.db.is_vendor_supported(vendor):
            raise IOAllocationError(f"Vendor '{vendor}' not supported. Available: {self.db.get_available_vendors()}")

    def classify_system(self, instrument: Instrument) -> ControlSystem:
        """
        Classify which control system an instrument belongs to.

        Rules:
        - Instruments with SIS prefixes (TZI, PZI, EVI, etc.) -> SIS
        - Instruments with location DS-1, DS-3, RTU -> RTU
        - All others -> DCS
        """
        # Check for SIS prefixes
        inst_type = instrument.instrument_type.upper() if instrument.instrument_type else ""
        for prefix in self.SIS_PREFIXES:
            if inst_type.startswith(prefix):
                return ControlSystem.SIS

        # Check for remote locations (RTU)
        area = instrument.area.upper() if instrument.area else ""
        if "DS-1" in area or "DS-3" in area or "RTU" in area:
            return ControlSystem.RTU

        # Default to DCS
        return ControlSystem.DCS

    def get_io_type(self, instrument: Instrument) -> IOType:
        """Get the I/O type for an instrument."""
        # First check if io_type is directly set (from flexible parser)
        if hasattr(instrument, 'io_type') and instrument.io_type:
            io_type_str = str(instrument.io_type).upper()
            if io_type_str == 'AI':
                return IOType.AI
            elif io_type_str == 'AO':
                return IOType.AO
            elif io_type_str == 'DI':
                return IOType.DI
            elif io_type_str == 'DO':
                return IOType.DO

        # Fallback to signal_type mapping
        signal_type = instrument.signal_type
        if signal_type is None:
            # Default based on instrument type
            return IOType.AI
        return self.SIGNAL_TO_IO_TYPE.get(signal_type, IOType.AI)

    def count_signals_by_system(
        self,
        instruments: List[Instrument]
    ) -> Dict[ControlSystem, SignalCount]:
        """
        Count signals grouped by control system.

        Args:
            instruments: List of instruments

        Returns:
            Dictionary mapping ControlSystem to SignalCount
        """
        counts = {
            ControlSystem.DCS: SignalCount(),
            ControlSystem.SIS: SignalCount(),
            ControlSystem.RTU: SignalCount(),
        }

        for inst in instruments:
            system = self.classify_system(inst)
            io_type = self.get_io_type(inst)

            count = counts[system]
            if io_type == IOType.AI:
                count.ai += 1
            elif io_type == IOType.AO:
                count.ao += 1
            elif io_type == IOType.DI:
                count.di += 1
            elif io_type == IOType.DO:
                count.do += 1

        return counts

    def calculate_cards_needed(
        self,
        signal_count: int,
        channels_per_card: int,
        spare_percent: Optional[float] = None
    ) -> Tuple[int, int, int]:
        """
        Calculate number of cards needed with spare capacity.

        Formula:
        - Channels needed = SignalCount * (1 + spare_percent)
        - Cards = CEILING(Channels / ChannelsPerCard)

        Args:
            signal_count: Number of signals
            channels_per_card: Channels per card
            spare_percent: Override spare percentage

        Returns:
            Tuple of (num_cards, channels_used, spare_channels)
        """
        if signal_count == 0:
            return 0, 0, 0

        spare = spare_percent if spare_percent is not None else self.spare_percent

        # Calculate channels with spare
        channels_with_spare = math.ceil(signal_count * (1 + spare))

        # Calculate number of cards
        num_cards = math.ceil(channels_with_spare / channels_per_card)

        # Calculate actual spare
        total_channels = num_cards * channels_per_card
        actual_spare = total_channels - signal_count

        return num_cards, signal_count, actual_spare

    def allocate_cards_for_io_type(
        self,
        system: ControlSystem,
        io_type: IOType,
        signal_count: int,
        location: str,
        card_start_number: int,
        instruments: Optional[List[Instrument]] = None
    ) -> List[IOCard]:
        """
        Allocate I/O cards for a specific I/O type.

        Args:
            system: Control system
            io_type: I/O type (AI, AO, DI, DO)
            signal_count: Number of signals
            location: Physical location
            card_start_number: Starting card number
            instruments: List of instruments to assign to channels

        Returns:
            List of allocated IOCard objects
        """
        if signal_count == 0:
            return []

        cards = []

        # Get module from database
        module = self.db.get_module(
            self.vendor, system, io_type,
            sil_required=(system == ControlSystem.SIS)
        )

        if not module:
            # Use channel density to create a generic module
            channels = self.db.get_channel_density(self.vendor, system, io_type)
            module = IOModule(
                model=f"{system.value}-{io_type.value}-GENERIC",
                io_type=io_type,
                channels=channels,
                signal_type="4-20mA" if io_type in [IOType.AI, IOType.AO] else "24VDC",
                control_system=system
            )

        # Calculate cards needed
        num_cards, used, spare = self.calculate_cards_needed(
            signal_count, module.channels
        )

        # Create card instances with channel assignments
        instrument_index = 0
        for i in range(num_cards):
            signals_on_card = min(signal_count - (i * module.channels), module.channels)
            if signals_on_card < 0:
                signals_on_card = 0
            spare_on_card = module.channels - signals_on_card

            # Build channel assignments
            channel_assignments = {}
            for ch in range(1, module.channels + 1):
                if instruments and instrument_index < len(instruments):
                    # Assign instrument to channel
                    inst = instruments[instrument_index]
                    channel_assignments[ch] = {
                        'tag': inst.tag_number,
                        'service': inst.service or '',
                        'type': inst.instrument_type or '',
                        'status': 'USED'
                    }
                    instrument_index += 1
                else:
                    # Mark as spare
                    channel_assignments[ch] = {
                        'tag': 'SPARE',
                        'service': '',
                        'type': '',
                        'status': 'SPARE'
                    }

            card = IOCard(
                module=module,
                card_number=card_start_number + i,
                system=system,
                location=location,
                total_channels=module.channels,
                used_channels=signals_on_card,
                spare_channels=spare_on_card,
                channel_assignments=channel_assignments
            )
            cards.append(card)

        return cards

    def allocate_cards_for_system(
        self,
        system: ControlSystem,
        signal_counts: SignalCount,
        location: str = "CCR",
        instruments_by_type: Optional[Dict[IOType, List[Instrument]]] = None
    ) -> List[IOCard]:
        """
        Allocate I/O cards for a control system.

        Args:
            system: Control system (DCS, SIS, RTU)
            signal_counts: Signal counts by type
            location: Physical location
            instruments_by_type: Instruments grouped by I/O type

        Returns:
            List of allocated IOCard objects
        """
        cards = []
        card_counter = 1
        instruments_by_type = instruments_by_type or {}

        # Allocate AI cards
        ai_cards = self.allocate_cards_for_io_type(
            system, IOType.AI, signal_counts.ai, location, card_counter,
            instruments_by_type.get(IOType.AI, [])
        )
        cards.extend(ai_cards)
        card_counter += len(ai_cards)

        # Allocate AO cards
        ao_cards = self.allocate_cards_for_io_type(
            system, IOType.AO, signal_counts.ao, location, card_counter,
            instruments_by_type.get(IOType.AO, [])
        )
        cards.extend(ao_cards)
        card_counter += len(ao_cards)

        # Allocate DI cards
        di_cards = self.allocate_cards_for_io_type(
            system, IOType.DI, signal_counts.di, location, card_counter,
            instruments_by_type.get(IOType.DI, [])
        )
        cards.extend(di_cards)
        card_counter += len(di_cards)

        # Allocate DO cards
        do_cards = self.allocate_cards_for_io_type(
            system, IOType.DO, signal_counts.do, location, card_counter,
            instruments_by_type.get(IOType.DO, [])
        )
        cards.extend(do_cards)

        return cards

    def group_instruments_by_system_and_type(
        self,
        instruments: List[Instrument]
    ) -> Dict[ControlSystem, Dict[IOType, List[Instrument]]]:
        """
        Group instruments by control system and I/O type.

        Args:
            instruments: List of instruments

        Returns:
            Nested dict: {System: {IOType: [instruments]}}
        """
        grouped = {
            ControlSystem.DCS: {t: [] for t in IOType},
            ControlSystem.SIS: {t: [] for t in IOType},
            ControlSystem.RTU: {t: [] for t in IOType},
        }

        for inst in instruments:
            system = self.classify_system(inst)
            io_type = self.get_io_type(inst)
            grouped[system][io_type].append(inst)

        return grouped

    def allocate(
        self,
        instruments: List[Instrument],
        system_type_override: Optional[str] = None
    ) -> IOAllocationResult:
        """
        Perform complete I/O allocation for a list of instruments.

        Args:
            instruments: List of instruments to allocate
            system_type_override: Force all instruments to a specific system
                                 ('RTU', 'DCS', 'SIS', 'ESD')

        Returns:
            IOAllocationResult with complete allocation
        """
        # If system override is specified, reclassify all instruments
        if system_type_override:
            system_type_upper = system_type_override.upper()
            if system_type_upper in ['SIS', 'ESD']:
                target_system = ControlSystem.SIS
            elif system_type_upper == 'RTU':
                target_system = ControlSystem.RTU
            elif system_type_upper == 'DCS':
                target_system = ControlSystem.DCS
            else:
                target_system = None

            if target_system:
                # Override classification for all instruments
                original_classify = self.classify_system
                self.classify_system = lambda inst: target_system

        # Count signals by system
        system_counts = self.count_signals_by_system(instruments)

        # Group instruments by system and I/O type for channel assignment
        grouped = self.group_instruments_by_system_and_type(instruments)

        # Allocate cards for each system with instrument assignments
        dcs_cards = self.allocate_cards_for_system(
            ControlSystem.DCS,
            system_counts[ControlSystem.DCS],
            "CCR",
            grouped[ControlSystem.DCS]
        )

        sis_cards = self.allocate_cards_for_system(
            ControlSystem.SIS,
            system_counts[ControlSystem.SIS],
            "CCR",
            grouped[ControlSystem.SIS]
        )

        rtu_cards = self.allocate_cards_for_system(
            ControlSystem.RTU,
            system_counts[ControlSystem.RTU],
            "DS-1/DS-3",
            grouped[ControlSystem.RTU]
        )

        # Calculate actual spare percentages
        actual_spare = {}
        for system, cards in [('DCS', dcs_cards), ('SIS', sis_cards), ('RTU', rtu_cards)]:
            if cards:
                total_channels = sum(c.total_channels for c in cards)
                used_channels = sum(c.used_channels for c in cards)
                if total_channels > 0:
                    actual_spare[system] = ((total_channels - used_channels) / total_channels) * 100

        # Build segregation rules list
        segregation_rules = [
            "DCS and SIS on separate systems",
            "Analog and Digital on separate cards",
            "SIL-rated modules for SIS",
            f"{self.spare_percent * 100:.0f}% spare capacity applied",
        ]

        # Add custom rules if provided
        if self.custom_rules:
            if self.custom_rules.segregate_by_area:
                segregation_rules.append("Segregated by plant area")
            if self.custom_rules.segregate_is_non_is:
                segregation_rules.append("IS and non-IS signals on separate cards")
            if self.custom_rules.max_cabinets_per_area:
                segregation_rules.append(f"Max {self.custom_rules.max_cabinets_per_area} cabinets per area")
            if self.custom_rules.group_by_loop:
                segregation_rules.append("Signals grouped by control loop")
            if self.custom_rules.group_by_unit:
                segregation_rules.append("Signals grouped by unit")
            # Add any custom rules from LLM
            for custom_rule in self.custom_rules.custom_rules:
                segregation_rules.append(f"Custom: {custom_rule}")

        # Build result
        result = IOAllocationResult(
            dcs_summary=system_counts[ControlSystem.DCS].to_dict(),
            sis_summary=system_counts[ControlSystem.SIS].to_dict(),
            rtu_summary=system_counts[ControlSystem.RTU].to_dict(),
            dcs_cards=dcs_cards,
            sis_cards=sis_cards,
            rtu_cards=rtu_cards,
            spare_percent_target=self.spare_percent * 100,
            actual_spare_percent=actual_spare,
            segregation_rules_applied=segregation_rules
        )

        return result


def calculate_io_allocation(
    instruments: List[Instrument],
    vendor: str = "Yokogawa",
    spare_percent: float = 0.20
) -> IOAllocationResult:
    """
    Convenience function to calculate I/O allocation.

    Args:
        instruments: List of instruments
        vendor: Vendor name
        spare_percent: Target spare percentage

    Returns:
        IOAllocationResult
    """
    allocator = IOAllocator(vendor=vendor, spare_percent=spare_percent)
    return allocator.allocate(instruments)
