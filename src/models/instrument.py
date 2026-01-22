"""Instrument data model for DCS interconnection diagrams."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class SignalType(Enum):
    """Signal type classification for instruments."""
    ANALOG_INPUT = "ANALOG_INPUT"
    ANALOG_OUTPUT = "ANALOG_OUTPUT"
    DIGITAL_INPUT = "DIGITAL_INPUT"
    DIGITAL_OUTPUT = "DIGITAL_OUTPUT"
    THERMOCOUPLE = "THERMOCOUPLE"
    RTD_3WIRE = "RTD_3WIRE"
    RTD_4WIRE = "RTD_4WIRE"


# Instrument type to signal type mapping
INSTRUMENT_CLASSIFICATION = {
    # Analog Inputs (4-20mA) - Transmitters
    "TIT": SignalType.ANALOG_INPUT,    # Temperature Indicator Transmitter
    "PIT": SignalType.ANALOG_INPUT,    # Pressure Indicator Transmitter
    "FIT": SignalType.ANALOG_INPUT,    # Flow Indicator Transmitter
    "LIT": SignalType.ANALOG_INPUT,    # Level Indicator Transmitter
    "PDT": SignalType.ANALOG_INPUT,    # Pressure Differential Transmitter
    "AIT": SignalType.ANALOG_INPUT,    # Analyzer Indicator Transmitter
    "WIT": SignalType.ANALOG_INPUT,    # Weight Indicator Transmitter
    "TT": SignalType.ANALOG_INPUT,     # Temperature Transmitter
    "PT": SignalType.ANALOG_INPUT,     # Pressure Transmitter
    "FT": SignalType.ANALOG_INPUT,     # Flow Transmitter
    "LT": SignalType.ANALOG_INPUT,     # Level Transmitter
    "TZT": SignalType.ANALOG_INPUT,    # Temperature Transmitter (SIS)
    "PZT": SignalType.ANALOG_INPUT,    # Pressure Transmitter (SIS)
    "FZT": SignalType.ANALOG_INPUT,    # Flow Transmitter (SIS)
    "LZT": SignalType.ANALOG_INPUT,    # Level Transmitter (SIS)

    # Analog Inputs - Indicators/Indications
    "TI": SignalType.ANALOG_INPUT,     # Temperature Indicator/Indication
    "PI": SignalType.ANALOG_INPUT,     # Pressure Indicator
    "FI": SignalType.ANALOG_INPUT,     # Flow Indicator
    "LI": SignalType.ANALOG_INPUT,     # Level Indicator
    "PDI": SignalType.ANALOG_INPUT,    # Pressure Differential Indicator
    "AI": SignalType.ANALOG_INPUT,     # Analyzer Indicator
    "TZI": SignalType.ANALOG_INPUT,    # Temperature Indicator (SIS)
    "PZI": SignalType.ANALOG_INPUT,    # Pressure Indicator (SIS)
    "FZI": SignalType.ANALOG_INPUT,    # Flow Indicator (SIS)
    "LZI": SignalType.ANALOG_INPUT,    # Level Indicator (SIS)

    # Analog Outputs (4-20mA) - Controllers
    "TIC": SignalType.ANALOG_OUTPUT,   # Temperature Indicating Controller
    "PIC": SignalType.ANALOG_OUTPUT,   # Pressure Indicating Controller
    "FIC": SignalType.ANALOG_OUTPUT,   # Flow Indicating Controller
    "LIC": SignalType.ANALOG_OUTPUT,   # Level Indicating Controller
    "AIC": SignalType.ANALOG_OUTPUT,   # Analysis Indicating Controller
    "PDIC": SignalType.ANALOG_OUTPUT,  # Pressure Differential Indicating Controller

    # Analog Outputs - Transducers/Converters
    "TY": SignalType.ANALOG_OUTPUT,    # Temperature Transducer/Converter
    "PY": SignalType.ANALOG_OUTPUT,    # Pressure Transducer
    "FY": SignalType.ANALOG_OUTPUT,    # Flow Transducer
    "LY": SignalType.ANALOG_OUTPUT,    # Level Transducer
    "TCV": SignalType.ANALOG_OUTPUT,   # Temperature Control Valve
    "PCV": SignalType.ANALOG_OUTPUT,   # Pressure Control Valve
    "FCV": SignalType.ANALOG_OUTPUT,   # Flow Control Valve
    "LCV": SignalType.ANALOG_OUTPUT,   # Level Control Valve

    # Digital Inputs (24VDC) - Position/Limit Switches
    "ZS": SignalType.DIGITAL_INPUT,    # Position Switch
    "ZSC": SignalType.DIGITAL_INPUT,   # Position Switch Closed
    "ZSO": SignalType.DIGITAL_INPUT,   # Position Switch Open
    "ZI": SignalType.DIGITAL_INPUT,    # Position Indicator
    "ZSL": SignalType.DIGITAL_INPUT,   # Position Switch Low/Limit
    "ZSH": SignalType.DIGITAL_INPUT,   # Position Switch High
    "EZSC": SignalType.DIGITAL_INPUT,  # Emergency Position Switch Closed
    "EZSO": SignalType.DIGITAL_INPUT,  # Emergency Position Switch Open
    "EZLO": SignalType.DIGITAL_INPUT,  # Emergency Limit Switch Open
    "EZLC": SignalType.DIGITAL_INPUT,  # Emergency Limit Switch Closed
    "EZA": SignalType.DIGITAL_INPUT,   # Emergency Position Alarm
    "BZSC": SignalType.DIGITAL_INPUT,  # Bypass Position Switch Closed
    "BZSO": SignalType.DIGITAL_INPUT,  # Bypass Position Switch Open

    # Digital Inputs - Pressure Switches
    "PSL": SignalType.DIGITAL_INPUT,   # Pressure Switch Low
    "PSH": SignalType.DIGITAL_INPUT,   # Pressure Switch High
    "PSLL": SignalType.DIGITAL_INPUT,  # Pressure Switch Low Low
    "PSHH": SignalType.DIGITAL_INPUT,  # Pressure Switch High High
    "PS": SignalType.DIGITAL_INPUT,    # Pressure Switch

    # Digital Inputs - Level Switches
    "LSL": SignalType.DIGITAL_INPUT,   # Level Switch Low
    "LSH": SignalType.DIGITAL_INPUT,   # Level Switch High
    "LSLL": SignalType.DIGITAL_INPUT,  # Level Switch Low Low
    "LSHH": SignalType.DIGITAL_INPUT,  # Level Switch High High
    "LS": SignalType.DIGITAL_INPUT,    # Level Switch

    # Digital Inputs - Flow Switches
    "FS": SignalType.DIGITAL_INPUT,    # Flow Switch
    "FSL": SignalType.DIGITAL_INPUT,   # Flow Switch Low
    "FSH": SignalType.DIGITAL_INPUT,   # Flow Switch High

    # Digital Inputs - Temperature Switches
    "TS": SignalType.DIGITAL_INPUT,    # Temperature Switch
    "TSL": SignalType.DIGITAL_INPUT,   # Temperature Switch Low
    "TSH": SignalType.DIGITAL_INPUT,   # Temperature Switch High
    "TSLL": SignalType.DIGITAL_INPUT,  # Temperature Switch Low Low
    "TSHH": SignalType.DIGITAL_INPUT,  # Temperature Switch High High

    # Digital Inputs - Alarms and Status
    "XS": SignalType.DIGITAL_INPUT,    # General Switch
    "XA": SignalType.DIGITAL_INPUT,    # General Alarm
    "TAH": SignalType.DIGITAL_INPUT,   # Temperature Alarm High
    "TAL": SignalType.DIGITAL_INPUT,   # Temperature Alarm Low
    "PAH": SignalType.DIGITAL_INPUT,   # Pressure Alarm High
    "PAL": SignalType.DIGITAL_INPUT,   # Pressure Alarm Low
    "LAH": SignalType.DIGITAL_INPUT,   # Level Alarm High
    "LAL": SignalType.DIGITAL_INPUT,   # Level Alarm Low
    "LAD": SignalType.DIGITAL_INPUT,   # Level Deviation Alarm
    "TAD": SignalType.DIGITAL_INPUT,   # Temperature Deviation Alarm
    "PAD": SignalType.DIGITAL_INPUT,   # Pressure Deviation Alarm
    "FAD": SignalType.DIGITAL_INPUT,   # Flow Deviation Alarm

    # Digital Inputs - Equipment Status
    "EEHZY": SignalType.DIGITAL_INPUT, # Electric Heater Running Status
    "YS": SignalType.DIGITAL_INPUT,    # Status/Running Switch
    "YA": SignalType.DIGITAL_INPUT,    # Status Alarm
    "YI": SignalType.DIGITAL_INPUT,    # Status Indicator

    # Digital Outputs (24VDC)
    "XV": SignalType.DIGITAL_OUTPUT,   # On/Off Valve
    "XY": SignalType.DIGITAL_OUTPUT,   # On/Off Relay/Solenoid
    "SOV": SignalType.DIGITAL_OUTPUT,  # Solenoid Valve
    "SDV": SignalType.DIGITAL_OUTPUT,  # Shutdown Valve
    "MOV": SignalType.DIGITAL_OUTPUT,  # Motor Operated Valve
    "HC": SignalType.DIGITAL_OUTPUT,   # Hand Controller
    "HS": SignalType.DIGITAL_OUTPUT,   # Hand Switch

    # Control Valves (Analog Output)
    "FV": SignalType.ANALOG_OUTPUT,    # Flow Control Valve
    "PV": SignalType.ANALOG_OUTPUT,    # Pressure Control Valve
    "LV": SignalType.ANALOG_OUTPUT,    # Level Control Valve
    "TV": SignalType.ANALOG_OUTPUT,    # Temperature Control Valve

    # RTD Types
    "TE": SignalType.RTD_3WIRE,        # Temperature Element (RTD)
}


@dataclass
class Instrument:
    """Represents an instrument in the DCS system."""

    tag_number: str                     # e.g., "PP01-364-TIT0001"
    instrument_type: str                # TIT, PIT, FIT, LIT, ZS, XV, etc.
    service: str                        # Service description
    area: str                           # Plant area code

    # Derived/assigned fields
    signal_type: Optional[SignalType] = None
    loop_number: Optional[str] = None   # Loop identifier
    cable_tag: Optional[str] = None     # Assigned branch cable tag
    jb_terminal_positive: Optional[str] = None   # Assigned JB terminal +
    jb_terminal_negative: Optional[str] = None   # Assigned JB terminal -
    jb_terminal_shield: Optional[str] = None     # Assigned JB shield terminal
    cabinet_terminal_pair: Optional[str] = None  # Assigned cabinet terminal pair
    cabinet_terminal_positive: Optional[str] = None
    cabinet_terminal_negative: Optional[str] = None

    # Optional metadata
    pid_reference: Optional[str] = None  # P&ID drawing number
    io_type: Optional[str] = None        # AI, AO, DI, DO
    remarks: Optional[str] = None        # Additional notes

    def __post_init__(self):
        """Auto-classify signal type if not provided."""
        if self.signal_type is None:
            self.signal_type = self.classify_signal_type()

    def classify_signal_type(self) -> SignalType:
        """Classify instrument signal type based on instrument type."""
        # Try exact match first
        if self.instrument_type in INSTRUMENT_CLASSIFICATION:
            return INSTRUMENT_CLASSIFICATION[self.instrument_type]

        # Try prefix matching for composite types
        for prefix in sorted(INSTRUMENT_CLASSIFICATION.keys(), key=len, reverse=True):
            if self.instrument_type.startswith(prefix):
                return INSTRUMENT_CLASSIFICATION[prefix]

        # Default to analog input if unknown
        return SignalType.ANALOG_INPUT

    @property
    def is_analog(self) -> bool:
        """Check if instrument is analog type."""
        return self.signal_type in [
            SignalType.ANALOG_INPUT,
            SignalType.ANALOG_OUTPUT,
            SignalType.THERMOCOUPLE,
            SignalType.RTD_3WIRE,
            SignalType.RTD_4WIRE
        ]

    @property
    def is_digital(self) -> bool:
        """Check if instrument is digital type."""
        return self.signal_type in [
            SignalType.DIGITAL_INPUT,
            SignalType.DIGITAL_OUTPUT
        ]

    @property
    def is_input(self) -> bool:
        """Check if instrument is an input type."""
        return self.signal_type in [
            SignalType.ANALOG_INPUT,
            SignalType.DIGITAL_INPUT,
            SignalType.THERMOCOUPLE,
            SignalType.RTD_3WIRE,
            SignalType.RTD_4WIRE
        ]

    @property
    def is_output(self) -> bool:
        """Check if instrument is an output type."""
        return self.signal_type in [
            SignalType.ANALOG_OUTPUT,
            SignalType.DIGITAL_OUTPUT
        ]

    @classmethod
    def from_dict(cls, data: dict) -> "Instrument":
        """Create Instrument from dictionary."""
        return cls(
            tag_number=data.get("Tag Number", data.get("tag_number", "")),
            instrument_type=data.get("Instrument Type", data.get("instrument_type", "")),
            service=data.get("Service Description", data.get("service", "")),
            area=data.get("Area", data.get("area", "")),
            loop_number=data.get("Loop Number", data.get("loop_number")),
            pid_reference=data.get("P&ID Reference", data.get("pid_reference")),
            io_type=data.get("IO Type", data.get("io_type")),
            remarks=data.get("Remarks", data.get("remarks")),
        )
