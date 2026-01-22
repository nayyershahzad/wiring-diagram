# DCS Interconnection Diagram Generator

An AI-powered tool that automatically generates professional DCS (Distributed Control System) interconnection diagrams in PDF format, eliminating the need for CAD software.

## Features

- **Excel I/O List Parser**: Read instrument data from Excel spreadsheets
- **Intelligent Classification**: Automatically classify instruments as analog/digital
- **Cable Sizing**: Calculate appropriate cable sizes with 20% spare capacity
- **Terminal Allocation**: Auto-assign terminals with proper spare allocation
- **PDF Generation**: Create professional A3 interconnection drawings
- **CLI Interface**: Easy-to-use command-line interface

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/dcs-interconnection-generator.git
cd dcs-interconnection-generator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## Quick Start

### Generate a Sample I/O List

```bash
python examples/create_sample_io_list.py
```

### Generate an Interconnection Diagram

```bash
python -m src.cli.main generate \
    --io-list examples/sample_io_list.xlsx \
    --jb-tag PP01-601-IAJB0001 \
    --cabinet-tag PP01-601-ICP001 \
    --output examples/output/diagram.pdf
```

### Validate an I/O List

```bash
python -m src.cli.main validate --io-list examples/sample_io_list.xlsx
```

### Generate Cable Schedule

```bash
python -m src.cli.main cable-schedule \
    --io-list examples/sample_io_list.xlsx \
    --output examples/output/cable_schedule.xlsx
```

### Interactive Mode

```bash
python -m src.cli.main interactive
```

## I/O List Format

The Excel I/O list should contain the following columns:

| Column | Required | Description |
|--------|----------|-------------|
| Tag Number | Yes | Instrument tag (e.g., PP01-364-TIT0001) |
| Instrument Type | Yes | Type code (TIT, PIT, FIT, ZS, XV, etc.) |
| Service Description | Yes | Process description |
| Area | Yes | Plant area code |
| IO Type | No | AI, AO, DI, or DO |
| Loop Number | No | Control loop reference |
| P&ID Reference | No | P&ID drawing number |
| Remarks | No | Additional notes |

## Supported Instrument Types

### Analog Inputs (4-20mA)
- TIT, PIT, FIT, LIT - Transmitters
- PDT, AIT, WIT - Differential/Analyzer/Weight

### Analog Outputs (4-20mA)
- FCV, PCV, LCV, TCV - Control Valves
- TY, PY, FY, LY - Transducers

### Digital Inputs (24VDC)
- ZS, ZSO, ZSC - Position Switches
- PSH, PSL, PSHH, PSLL - Pressure Switches
- LSH, LSL, LSHH, LSLL - Level Switches
- FS, FSH, FSL - Flow Switches
- TS, TSH, TSL - Temperature Switches

### Digital Outputs (24VDC)
- XV, XY - On/Off Valves/Relays
- SOV, SDV - Solenoid/Shutdown Valves

## Project Structure

```
dcs-interconnection-generator/
├── src/
│   ├── models/          # Data models
│   ├── parsers/         # Excel parsing
│   ├── engine/          # Business logic
│   ├── drawing/         # SVG/PDF generation
│   └── cli/             # Command-line interface
├── config/              # Configuration files
├── examples/            # Sample files
├── tests/               # Unit tests
└── docs/                # Documentation
```

## Configuration

Configuration files are located in the `config/` directory:

- `cable_rules.yaml` - Cable sizing rules
- `terminal_rules.yaml` - Terminal allocation rules
- `drawing_config.yaml` - Drawing dimensions and styles

## API Usage

```python
from src import (
    load_io_list,
    filter_instruments_by_area,
    classify_jb_type,
    allocate_all_terminals,
    size_cables_for_jb,
    render_interconnection_diagram,
)

# Load I/O list
result = load_io_list("io_list.xlsx")
instruments = result.instruments

# Filter by area
area_364_instruments = filter_instruments_by_area(instruments, "364")

# Classify JB type
jb_type = classify_jb_type(area_364_instruments)
print(f"JB Type: {jb_type.value}")  # ANALOG or DIGITAL

# Generate diagram
render_interconnection_diagram(
    instruments=area_364_instruments,
    jb_tag="PP01-601-IAJB0001",
    cabinet_tag="PP01-601-ICP001",
    multipair_cable_tag="PP01-601-I0001",
    tb_tag="TB601-I0001",
    output_path="diagram.pdf",
)
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/
flake8 src/
```

## License

MIT License - see LICENSE file for details.

## Author

Nayyer

## Acknowledgments

- Designed for Rumaila Oil Field EPP project standards
- Based on IEC 61082 and ISA-5.1 standards
