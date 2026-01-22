# DCS Interconnection Diagram Generator

## Project Overview

An AI-powered tool that automatically generates professional DCS (Distributed Control System) interconnection diagrams in PDF format, eliminating the need for CAD software. The tool reads instrument I/O lists from Excel, applies intelligent cable sizing and terminal allocation rules, and produces construction-ready interconnection drawings.

### Target Output
Generate PDF interconnection diagrams matching the style of Rumaila Oil Field EPP (Early Power Plant) project drawings (100478CP-N-PG-PP01-IC-DIC-0004 series).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      INPUT LAYER                                 │
├─────────────────────────────────────────────────────────────────┤
│  • Excel I/O List (Instrument Tag, Type, Service, etc.)         │
│  • User Input: JB Tag Number, Cabinet Tag Number                │
│  • Project Configuration (Project No, Title, Revision)          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PROCESSING ENGINE                              │
├─────────────────────────────────────────────────────────────────┤
│  1. I/O List Parser (pandas)                                    │
│  2. Instrument Classifier (Analog/Digital/Direct Run)           │
│  3. Cable Sizing Engine                                         │
│  4. Terminal Allocation Engine (with 20% spare logic)           │
│  5. Tag Number Generator                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   DRAWING ENGINE                                 │
├─────────────────────────────────────────────────────────────────┤
│  • SVG Primitives Generator                                     │
│  • Layout Calculator                                            │
│  • Title Block Generator                                        │
│  • PDF Renderer (ReportLab/svglib)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      OUTPUT                                      │
├─────────────────────────────────────────────────────────────────┤
│  • Multi-page PDF with interconnection diagrams                 │
│  • Cable schedule summary                                       │
│  • Terminal allocation report                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
dcs-interconnection-generator/
├── CLAUDE.md                    # This file
├── README.md                    # User documentation
├── requirements.txt             # Python dependencies
├── setup.py                     # Package setup
│
├── src/
│   ├── __init__.py
│   │
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── io_list_parser.py    # Excel I/O list parser
│   │   └── validators.py        # Input validation
│   │
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── classifier.py        # Instrument type classifier
│   │   ├── cable_sizer.py       # Cable sizing logic
│   │   ├── terminal_allocator.py # Terminal allocation with spares
│   │   └── tag_generator.py     # Tag numbering system
│   │
│   ├── drawing/
│   │   ├── __init__.py
│   │   ├── primitives.py        # SVG drawing primitives
│   │   ├── components/
│   │   │   ├── __init__.py
│   │   │   ├── instrument.py    # Instrument symbol
│   │   │   ├── junction_box.py  # JB terminal block
│   │   │   ├── cable.py         # Cable representation
│   │   │   ├── marshalling.py   # Marshalling cabinet TB
│   │   │   └── title_block.py   # Drawing title block
│   │   ├── layout.py            # Page layout calculator
│   │   └── renderer.py          # SVG to PDF renderer
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── instrument.py        # Instrument data model
│   │   ├── cable.py             # Cable data model
│   │   ├── terminal.py          # Terminal data model
│   │   └── drawing.py           # Drawing metadata model
│   │
│   └── cli/
│       ├── __init__.py
│       └── main.py              # Command-line interface
│
├── config/
│   ├── cable_rules.yaml         # Cable sizing rules
│   ├── terminal_rules.yaml      # Terminal allocation rules
│   └── drawing_config.yaml      # Drawing dimensions/styles
│
├── templates/
│   └── title_block.svg          # Title block template
│
├── tests/
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_engine.py
│   └── test_drawing.py
│
├── examples/
│   ├── sample_io_list.xlsx      # Sample I/O list
│   └── output/                  # Generated PDFs
│
└── docs/
    ├── cable_sizing_rules.md
    └── terminal_allocation.md
```

---

## Data Models

### 1. Instrument Model
```python
@dataclass
class Instrument:
    tag_number: str          # e.g., "PP01-364-TIT0001"
    instrument_type: str     # TIT, PIT, FIT, LIT, ZS, XV, etc.
    signal_type: str         # "ANALOG_INPUT", "ANALOG_OUTPUT", "DIGITAL_INPUT", "DIGITAL_OUTPUT"
    service: str             # Service description
    area: str                # Plant area code
    loop_number: str         # Loop identifier
    cable_tag: str           # Assigned branch cable tag
    jb_terminal: str         # Assigned JB terminal
    cabinet_terminal: str    # Assigned cabinet terminal
```

### 2. Cable Model
```python
@dataclass
class Cable:
    tag_number: str          # e.g., "PP01-601-I0004"
    cable_type: str          # "BRANCH" or "MULTIPAIR"
    specification: str       # "1Px1.5mm2", "5PRx1.0mm2", etc.
    pair_count: int          # Number of pairs
    from_location: str       # Source (Instrument or JB)
    to_location: str         # Destination (JB or Cabinet)
    length_meters: float     # Optional: cable length
```

### 3. Terminal Block Model
```python
@dataclass
class TerminalBlock:
    tag_number: str          # e.g., "TB601-I0004"
    location: str            # "JB" or "CABINET"
    parent_equipment: str    # JB or Cabinet tag
    total_terminals: int     # Total available terminals
    used_terminals: int      # Used terminals
    spare_terminals: int     # Spare terminals (target 20%)
    allocations: List[TerminalAllocation]
```

### 4. Drawing Sheet Model
```python
@dataclass
class DrawingSheet:
    sheet_number: int
    drawing_number: str      # e.g., "100478CP-N-PG-PP01-IC-DIC-0004-004"
    title: str               # e.g., "PP01-601-IAJB0002 (ANALOG JB)"
    revision: str
    date: str
    instruments: List[Instrument]
    junction_box: JunctionBox
    multipair_cable: Cable
    marshalling_cabinet: MarshallingCabinet
```

---

## Instrument Classification Rules

### Signal Type Classification
```python
INSTRUMENT_CLASSIFICATION = {
    # Analog Inputs (4-20mA)
    "TIT": "ANALOG_INPUT",    # Temperature Indicator Transmitter
    "PIT": "ANALOG_INPUT",    # Pressure Indicator Transmitter
    "FIT": "ANALOG_INPUT",    # Flow Indicator Transmitter
    "LIT": "ANALOG_INPUT",    # Level Indicator Transmitter
    "PDT": "ANALOG_INPUT",    # Pressure Differential Transmitter
    "AIT": "ANALOG_INPUT",    # Analyzer Indicator Transmitter
    "WIT": "ANALOG_INPUT",    # Weight Indicator Transmitter
    
    # Analog Outputs (4-20mA)
    "TY": "ANALOG_OUTPUT",    # Temperature Transducer/Converter
    "PY": "ANALOG_OUTPUT",    # Pressure Transducer
    "FY": "ANALOG_OUTPUT",    # Flow Transducer
    "LY": "ANALOG_OUTPUT",    # Level Transducer
    
    # Digital Inputs (24VDC)
    "ZS": "DIGITAL_INPUT",    # Position Switch
    "ZSC": "DIGITAL_INPUT",   # Position Switch Closed
    "ZSO": "DIGITAL_INPUT",   # Position Switch Open
    "EZSC": "DIGITAL_INPUT",  # Emergency Position Switch Closed
    "EZSO": "DIGITAL_INPUT",  # Emergency Position Switch Open
    "BZSC": "DIGITAL_INPUT",  # Bypass Position Switch Closed
    "BZSO": "DIGITAL_INPUT",  # Bypass Position Switch Open
    "PSL": "DIGITAL_INPUT",   # Pressure Switch Low
    "PSH": "DIGITAL_INPUT",   # Pressure Switch High
    "PSLL": "DIGITAL_INPUT",  # Pressure Switch Low Low
    "PSHH": "DIGITAL_INPUT",  # Pressure Switch High High
    "LSL": "DIGITAL_INPUT",   # Level Switch Low
    "LSH": "DIGITAL_INPUT",   # Level Switch High
    "FS": "DIGITAL_INPUT",    # Flow Switch
    "TS": "DIGITAL_INPUT",    # Temperature Switch
    "XS": "DIGITAL_INPUT",    # General Switch
    
    # Digital Outputs (24VDC)
    "XV": "DIGITAL_OUTPUT",   # On/Off Valve
    "XY": "DIGITAL_OUTPUT",   # On/Off Relay/Solenoid
    "SOV": "DIGITAL_OUTPUT",  # Solenoid Valve
    
    # Control Valves (Analog Output)
    "FV": "ANALOG_OUTPUT",    # Flow Control Valve
    "PV": "ANALOG_OUTPUT",    # Pressure Control Valve
    "LV": "ANALOG_OUTPUT",    # Level Control Valve
    "TV": "ANALOG_OUTPUT",    # Temperature Control Valve
}
```

### Junction Box Type Classification
```python
def classify_jb_type(instruments: List[Instrument]) -> str:
    """Classify JB as ANALOG or DIGITAL based on instruments."""
    signal_types = {inst.signal_type for inst in instruments}
    
    if all(st in ["ANALOG_INPUT", "ANALOG_OUTPUT"] for st in signal_types):
        return "ANALOG"
    elif all(st in ["DIGITAL_INPUT", "DIGITAL_OUTPUT"] for st in signal_types):
        return "DIGITAL"
    else:
        return "MIXED"  # Should be avoided in design
```

---

## Cable Sizing Rules

### Branch Cables (Instrument to JB)
```python
BRANCH_CABLE_RULES = {
    "ANALOG_INPUT": {
        "specification": "1Px1.5mm2",
        "pair_count": 1,
        "description": "Single pair, 1.5mm² for 4-20mA signals"
    },
    "ANALOG_OUTPUT": {
        "specification": "1Px1.5mm2",
        "pair_count": 1,
        "description": "Single pair, 1.5mm² for 4-20mA signals"
    },
    "DIGITAL_INPUT": {
        "specification": "1Px1.5mm2",
        "pair_count": 1,
        "description": "Single pair, 1.5mm² for 24VDC signals"
    },
    "DIGITAL_OUTPUT": {
        "specification": "1Px1.5mm2",
        "pair_count": 1,
        "description": "Single pair, 1.5mm² for 24VDC signals"
    },
    "THERMOCOUPLE": {
        "specification": "1Px1.5mm2",  # Compensating cable
        "pair_count": 1,
        "description": "Thermocouple compensating cable"
    },
    "RTD_3WIRE": {
        "specification": "3Cx1.5mm2",
        "pair_count": 1,  # Treated as 1 allocation
        "description": "3-wire RTD cable"
    },
    "RTD_4WIRE": {
        "specification": "2Px1.5mm2",
        "pair_count": 2,
        "description": "4-wire RTD cable"
    }
}
```

### Multipair Cables (JB to Marshalling Cabinet)
```python
MULTIPAIR_CABLE_SIZES = [5, 10, 20]  # Standard pair counts

def calculate_multipair_size(instrument_count: int, spare_percent: float = 0.20) -> int:
    """
    Calculate required multipair cable size with spare capacity.
    
    Args:
        instrument_count: Number of instruments (pairs needed)
        spare_percent: Target spare percentage (default 20%)
    
    Returns:
        Selected multipair cable size (5, 10, or 20 pairs)
    """
    required_with_spare = math.ceil(instrument_count * (1 + spare_percent))
    
    for size in MULTIPAIR_CABLE_SIZES:
        if size >= required_with_spare:
            return size
    
    # If more than 20 pairs needed, use multiple cables
    return 20  # Will need multiple cables

MULTIPAIR_CABLE_SPECS = {
    5: "5PRx1.0mm2",
    10: "10PRx1.0mm2",
    20: "20PRx1.0mm2"
}
```

---

## Terminal Allocation Rules

### JB Terminal Allocation
```python
def allocate_jb_terminals(
    instruments: List[Instrument],
    jb_tag: str,
    spare_percent: float = 0.20
) -> Dict[str, TerminalAllocation]:
    """
    Allocate JB terminals for instruments with 20% spare.
    
    Terminal naming convention:
    - Signal terminals: 1+, 1-, 2+, 2-, ... (for each pair)
    - Shield terminals: 1S, 2S, 3S, ... (one per instrument)
    - Overall shield: 0S (connected to earth bar)
    
    Example for 4 instruments:
    - Terminals 1+/1-, 2+/2-, 3+/3-, 4+/4- used
    - Terminals 5+/5- spare (20% of 4 = 0.8, rounded up = 1)
    - Shields: 1S, 2S, 3S, 4S, 5S (including spare)
    """
    total_instruments = len(instruments)
    spare_count = math.ceil(total_instruments * spare_percent)
    total_terminals = total_instruments + spare_count
    
    allocations = {}
    
    for idx, instrument in enumerate(instruments, start=1):
        allocations[instrument.tag_number] = TerminalAllocation(
            terminal_positive=f"{idx}+",
            terminal_negative=f"{idx}-",
            terminal_shield=f"{idx}S",
            instrument_tag=instrument.tag_number,
            status="USED"
        )
    
    # Add spare terminals
    for idx in range(total_instruments + 1, total_terminals + 1):
        allocations[f"SPARE_{idx}"] = TerminalAllocation(
            terminal_positive=f"{idx}+",
            terminal_negative=f"{idx}-",
            terminal_shield=f"{idx}S",
            instrument_tag="SPARE",
            status="SPARE"
        )
    
    return allocations
```

### Marshalling Cabinet Terminal Allocation
```python
def allocate_cabinet_terminals(
    instruments: List[Instrument],
    cabinet_tag: str,
    tb_tag: str,
    spare_percent: float = 0.20
) -> Dict[str, TerminalAllocation]:
    """
    Allocate marshalling cabinet terminals with 20% spare.
    
    Terminal naming convention:
    - Terminal block pairs: PR1, PR2, PR3, ... PR20 (max 20 per TB)
    - Each PRx has: x+, x- for signal
    - Overall shield: 0S (to instrument earth bar)
    
    Cabinet terminal format: WH/BK (White/Black) for polarity indication
    """
    total_instruments = len(instruments)
    spare_count = math.ceil(total_instruments * spare_percent)
    total_pairs = total_instruments + spare_count
    
    # Check if multiple terminal blocks needed
    if total_pairs > 20:
        raise ValueError(f"Requires multiple terminal blocks. Total pairs: {total_pairs}")
    
    allocations = {}
    
    for idx, instrument in enumerate(instruments, start=1):
        allocations[instrument.tag_number] = TerminalAllocation(
            terminal_pair=f"PR{idx}",
            terminal_positive=f"{idx}+",
            terminal_negative=f"{idx}-",
            wire_color_positive="WH",  # White
            wire_color_negative="BK",  # Black
            instrument_tag=instrument.tag_number,
            dcs_tag=instrument.tag_number,  # Same as instrument for now
            status="USED"
        )
    
    # Add spare terminals
    for idx in range(total_instruments + 1, total_pairs + 1):
        allocations[f"SPARE_{idx}"] = TerminalAllocation(
            terminal_pair=f"PR{idx}",
            terminal_positive=f"{idx}+",
            terminal_negative=f"{idx}-",
            wire_color_positive="WH",
            wire_color_negative="BK",
            instrument_tag="SPARE",
            dcs_tag="SPARE",
            status="SPARE"
        )
    
    return allocations
```

---

## Drawing Specifications

### Page Layout (A3 Size)
```python
DRAWING_CONFIG = {
    "page_size": "A3",
    "width_mm": 420,
    "height_mm": 297,
    "margin_left_mm": 20,
    "margin_right_mm": 10,
    "margin_top_mm": 10,
    "margin_bottom_mm": 10,
    "title_block_height_mm": 45,
    "notes_width_mm": 60,
}
```

### Drawing Zones
```
┌────────────────────────────────────────────────────────────────────────┐
│                                                            │  NOTES   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────┴────────┐ │
│  │ EPP-FIELD   │  │ JUNCTION    │  │ MULTIPAIR   │  │ DCS (EPP) CCR │ │
│  │             │  │ BOX         │  │             │  │               │ │
│  │ INSTRUMENT  │  │             │  │             │  │ MARSHALLING   │ │
│  │             │  │             │  │             │  │ CABINET       │ │
│  │             │  │             │  │             │  │               │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └───────────────┘ │
│                                                                        │
│  Zone 1          Zone 2           Zone 3          Zone 4      Zone 5  │
│  (15%)           (25%)            (15%)           (30%)       (15%)   │
├────────────────────────────────────────────────────────────────────────┤
│                         TITLE BLOCK                                    │
└────────────────────────────────────────────────────────────────────────┘
```

### Column Layout
```python
COLUMN_LAYOUT = {
    "zone1_instrument": {
        "x_start_percent": 0.02,
        "width_percent": 0.15,
        "header": "EPP-FIELD\nINSTRUMENT"
    },
    "zone2_junction_box": {
        "x_start_percent": 0.17,
        "width_percent": 0.25,
        "header": "JUNCTION BOX"
    },
    "zone3_multipair": {
        "x_start_percent": 0.42,
        "width_percent": 0.13,
        "header": "MULTIPAIR"
    },
    "zone4_cabinet": {
        "x_start_percent": 0.55,
        "width_percent": 0.30,
        "header": "DCS (EPP) CCR\nMARSHALLING CABINET"
    },
    "zone5_notes": {
        "x_start_percent": 0.85,
        "width_percent": 0.15,
        "header": "NOTES:"
    }
}
```

### Drawing Elements

#### Instrument Symbol
```
    ┌─────────────────┐
    │ PP01-364-TIT0001│────┬─── + ─── WH
    └─────────────────┘    │
                          └─── - ─── BK
```

#### Junction Box Terminal Block
```
    ┌─────────────────────────────────┐
    │      PP01-601-IAJB0002          │
    ├─────────────────────────────────┤
    │                                 │
    │  ○─┬─ 1+ ────────── WH ───○ PR1 │
    │    └─ 1- ────────── BK ───○     │
    │      1S ─┐                      │
    │  ○─┬─ 2+ ────────── WH ───○ PR2 │
    │    └─ 2- ────────── BK ───○     │
    │      2S ─┤                      │
    │         ...                     │
    │      0S ─┴───────────────────── │ ← To Earth Bar
    └─────────────────────────────────┘
```

#### Marshalling Cabinet Terminal Block
```
    ┌─────────────────────────────────┐
    │      PP01-601-ICP001            │
    ├─────────────────────────────────┤
    │      TB601-I0004                │
    ├─────────────────────────────────┤
    │                      DCS TAG    │
    │  PR1 ○──┬─ WH ── 1+ ─┐         │
    │         └─ BK ── 1- ─┴─ PP01-364-TIT0001
    │  PR2 ○──┬─ WH ── 2+ ─┐         │
    │         └─ BK ── 2- ─┴─ PP01-364-PIT0001
    │         ...                     │
    │                                 │
    │      0S ────────────────────────│ ← INSTRUMENT
    │         ◎                       │   EARTH BAR
    └─────────────────────────────────┘
```

---

## Tag Numbering Convention

### Instrument Tag Format
```
PP01-XXX-YYYNNNN

Where:
- PP01: Plant/Unit code
- XXX: Area/System code (e.g., 364, 512, 610)
- YYY: Instrument type (TIT, PIT, FIT, etc.)
- NNNN: Sequential number (0001, 0002, etc.)

Examples:
- PP01-364-TIT0001: Temperature transmitter in area 364
- PP01-512-PIT0002: Pressure transmitter in area 512
```

### Junction Box Tag Format
```
PP01-601-IAJB00XX (Analog JB)
PP01-601-IDJB00XX (Digital JB)

Where:
- PP01: Plant/Unit code
- 601: JB area code
- IA: Instrument Analog
- ID: Instrument Digital
- JB: Junction Box
- 00XX: Sequential number
```

### Cable Tag Format
```
Branch Cable: PP01-XXX-YYYNNNN (same as instrument tag)
Multipair: PP01-601-I00XX

Where:
- I00XX: Sequential cable number
```

### Terminal Block Tag Format
```
TB601-I00XX

Where:
- TB: Terminal Block
- 601: Area code (same as JB)
- I: Instrument
- 00XX: Sequential number matching multipair cable
```

---

## Excel I/O List Format

### Expected Columns
```python
IO_LIST_COLUMNS = {
    "required": [
        "Tag Number",           # Instrument tag (PP01-364-TIT0001)
        "Instrument Type",      # TIT, PIT, FIT, etc.
        "Service Description",  # Process description
        "Signal Type",          # 4-20mA, 24VDC, etc.
        "Area",                 # Plant area code
    ],
    "optional": [
        "Loop Number",          # Control loop reference
        "P&ID Reference",       # P&ID drawing number
        "IO Type",              # AI, AO, DI, DO
        "Cabinet",              # Pre-assigned cabinet
        "JB",                   # Pre-assigned JB
        "Remarks",              # Additional notes
    ]
}
```

### Sample I/O List Structure
| Tag Number | Instrument Type | Service Description | Signal Type | Area | IO Type |
|------------|-----------------|---------------------|-------------|------|---------|
| PP01-364-TIT0001 | TIT | Lube Oil Temperature | 4-20mA | 364 | AI |
| PP01-364-PIT0001 | PIT | Lube Oil Pressure | 4-20mA | 364 | AI |
| PP01-361-ZS0003 | ZS | Valve Position | 24VDC | 361 | DI |

---

## CLI Interface

### Commands
```bash
# Generate interconnection diagrams from I/O list
python -m src.cli.main generate \
    --io-list path/to/io_list.xlsx \
    --jb-tag PP01-601-IAJB0002 \
    --cabinet-tag PP01-601-ICP001 \
    --output output/diagrams.pdf

# Interactive mode
python -m src.cli.main interactive

# Validate I/O list format
python -m src.cli.main validate --io-list path/to/io_list.xlsx

# Generate cable schedule
python -m src.cli.main cable-schedule \
    --io-list path/to/io_list.xlsx \
    --output output/cable_schedule.xlsx
```

### Interactive Mode Flow
```
1. Load I/O List
   > Enter path to I/O list Excel file: sample_io_list.xlsx
   ✓ Loaded 45 instruments

2. Select Instruments for JB
   > Filter by area (or 'all'): 364
   > Found 12 instruments in area 364
   
3. Configure JB
   > Enter JB tag number: PP01-601-IAJB0002
   > JB Type detected: ANALOG (based on instrument types)
   > Calculated: 12 instruments + 3 spare = 15 terminals
   > Multipair cable size: 20PRx1.0mm2

4. Configure Cabinet
   > Enter Cabinet tag: PP01-601-ICP001
   > Enter TB tag (or auto): auto
   > Generated TB tag: TB601-I0004

5. Generate Drawing
   > Output filename: PP01-601-IAJB0002.pdf
   ✓ Generated interconnection diagram
   ✓ Saved to output/PP01-601-IAJB0002.pdf
```

---

## Implementation Phases

### Phase 1: Core Data Models & Parser (Week 1)
- [ ] Implement data models (Instrument, Cable, Terminal, Drawing)
- [ ] Build Excel I/O list parser with validation
- [ ] Create instrument classifier
- [ ] Unit tests for parser and classifier

### Phase 2: Engine Logic (Week 2)
- [ ] Implement cable sizing engine
- [ ] Build terminal allocation engine with 20% spare logic
- [ ] Create tag number generator
- [ ] Unit tests for all engine components

### Phase 3: Drawing Generator (Week 3-4)
- [ ] Build SVG primitives library
- [ ] Implement component drawings (instrument, JB, cabinet)
- [ ] Create layout calculator
- [ ] Build title block generator
- [ ] Implement PDF renderer

### Phase 4: CLI & Integration (Week 5)
- [ ] Build CLI interface
- [ ] Implement interactive mode
- [ ] Integration testing
- [ ] Documentation

### Phase 5: Enhancement (Week 6+)
- [ ] Add support for multiple JBs per drawing
- [ ] Implement MARK VI ES interface drawings
- [ ] Add LCP (Local Control Panel) support
- [ ] Create web interface (optional)

---

## Dependencies

```
# requirements.txt
pandas>=2.0.0          # Excel parsing
openpyxl>=3.1.0        # Excel file support
pyyaml>=6.0            # Configuration files
svgwrite>=1.4.0        # SVG generation
reportlab>=4.0.0       # PDF generation
svglib>=1.5.0          # SVG to PDF conversion
click>=8.0.0           # CLI framework
rich>=13.0.0           # Terminal formatting
pydantic>=2.0.0        # Data validation
pytest>=7.0.0          # Testing
```

---

## Testing Strategy

### Unit Tests
```python
# Test instrument classification
def test_classify_tit_as_analog_input():
    assert classify_instrument("TIT") == "ANALOG_INPUT"

# Test cable sizing
def test_multipair_sizing_with_spare():
    assert calculate_multipair_size(4) == 5   # 4 + 20% = 5
    assert calculate_multipair_size(5) == 10  # 5 + 20% = 6, needs 10PR
    assert calculate_multipair_size(16) == 20 # 16 + 20% = 20

# Test terminal allocation
def test_terminal_allocation_creates_spare():
    instruments = create_test_instruments(4)
    allocations = allocate_jb_terminals(instruments, "JB001")
    assert len([a for a in allocations.values() if a.status == "SPARE"]) == 1
```

### Integration Tests
```python
# Test full workflow
def test_generate_diagram_from_io_list():
    io_list = load_io_list("test_io_list.xlsx")
    instruments = parse_instruments(io_list)
    
    drawing = generate_interconnection_diagram(
        instruments=instruments,
        jb_tag="PP01-601-IAJB0002",
        cabinet_tag="PP01-601-ICP001"
    )
    
    assert drawing.sheet_count >= 1
    assert drawing.instruments == instruments
```

---

## Error Handling

### Validation Errors
```python
class IOListValidationError(Exception):
    """Raised when I/O list has invalid format or data."""
    pass

class TerminalOverflowError(Exception):
    """Raised when more terminals needed than available."""
    pass

class CableSizingError(Exception):
    """Raised when cable cannot be sized for given parameters."""
    pass
```

### User-Friendly Messages
```python
VALIDATION_MESSAGES = {
    "missing_column": "I/O list is missing required column: {column}",
    "invalid_tag": "Invalid instrument tag format: {tag}. Expected: PP01-XXX-YYYNNNN",
    "unknown_type": "Unknown instrument type: {type}. Valid types: {valid_types}",
    "terminal_overflow": "Too many instruments ({count}) for single JB. Maximum: 20",
}
```

---

## Configuration Files

### cable_rules.yaml
```yaml
branch_cables:
  analog:
    specification: "1Px1.5mm2"
    pair_count: 1
  digital:
    specification: "1Px1.5mm2"
    pair_count: 1
  rtd_3wire:
    specification: "3Cx1.5mm2"
    pair_count: 1
  rtd_4wire:
    specification: "2Px1.5mm2"
    pair_count: 2

multipair_cables:
  sizes: [5, 10, 20]
  specification_template: "{size}PRx1.0mm2"
  spare_percent: 0.20
```

### drawing_config.yaml
```yaml
page:
  size: A3
  width_mm: 420
  height_mm: 297
  orientation: landscape

margins:
  left_mm: 20
  right_mm: 10
  top_mm: 10
  bottom_mm: 10

title_block:
  height_mm: 45
  company: "CHINA PETROLEUM ENGINEERING & CONSTRUCTION CORP."
  project: "EARLY POWER PLANT\nRUMAILA OIL FIELD"
  contract: "100478"

fonts:
  primary: "Arial"
  size_title: 12
  size_normal: 8
  size_small: 6

colors:
  line: "#000000"
  text: "#000000"
  background: "#FFFFFF"

line_weights:
  thin: 0.25
  normal: 0.5
  thick: 1.0
  border: 0.7
```

---

## Notes for Claude Code

### Key Implementation Guidelines

1. **Start with data models** - Get the data structures right first
2. **Test-driven development** - Write tests before implementation
3. **Modular design** - Keep components loosely coupled
4. **Configuration over code** - Use YAML for rules that might change
5. **Progressive enhancement** - Start simple, add features incrementally

### Drawing Generation Tips

1. Use SVG as intermediate format (easier to debug)
2. Calculate all positions before drawing
3. Use relative positioning within zones
4. Handle text overflow gracefully
5. Generate title block separately (can be templated)

### Common Pitfalls to Avoid

1. Don't hardcode terminal counts - use configuration
2. Don't assume all instruments have same cable type
3. Handle multi-page drawings from the start
4. Consider DPI/resolution for PDF output
5. Validate all user inputs before processing

---

## Quick Start Commands

```bash
# Create project structure
mkdir -p dcs-interconnection-generator/{src/{parsers,engine,drawing/components,models,cli},config,templates,tests,examples,docs}

# Initialize Python package
touch dcs-interconnection-generator/src/__init__.py
touch dcs-interconnection-generator/src/{parsers,engine,drawing,models,cli}/__init__.py
touch dcs-interconnection-generator/src/drawing/components/__init__.py

# Create requirements.txt
cat > dcs-interconnection-generator/requirements.txt << EOF
pandas>=2.0.0
openpyxl>=3.1.0
pyyaml>=6.0
svgwrite>=1.4.0
reportlab>=4.0.0
svglib>=1.5.0
click>=8.0.0
rich>=13.0.0
pydantic>=2.0.0
pytest>=7.0.0
EOF

# Install dependencies
cd dcs-interconnection-generator
pip install -r requirements.txt
```

---

## Reference Documents

- Sample interconnection diagram: `100478CP-N-PG-PP01-IC-DIC-0004` (provided)
- ISA-5.1 Instrumentation Symbols and Identification
- IEC 61082 Preparation of Documents Used in Electrotechnology

---

*Last Updated: December 2024*
*Author: Nayyer / Claude*
