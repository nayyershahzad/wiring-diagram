"""Script to create a sample I/O list Excel file for testing."""

import pandas as pd
from pathlib import Path


def create_sample_io_list():
    """Create a sample I/O list Excel file."""

    # Sample instrument data
    instruments = [
        # Area 364 - Temperature instruments (Analog)
        {"Tag Number": "PP01-364-TIT0001", "Instrument Type": "TIT", "Service Description": "Lube Oil Temperature", "Area": "364", "IO Type": "AI"},
        {"Tag Number": "PP01-364-TIT0002", "Instrument Type": "TIT", "Service Description": "Bearing Temperature A", "Area": "364", "IO Type": "AI"},
        {"Tag Number": "PP01-364-TIT0003", "Instrument Type": "TIT", "Service Description": "Bearing Temperature B", "Area": "364", "IO Type": "AI"},
        {"Tag Number": "PP01-364-TIT0004", "Instrument Type": "TIT", "Service Description": "Exhaust Gas Temperature", "Area": "364", "IO Type": "AI"},

        # Area 364 - Pressure instruments (Analog)
        {"Tag Number": "PP01-364-PIT0001", "Instrument Type": "PIT", "Service Description": "Lube Oil Pressure", "Area": "364", "IO Type": "AI"},
        {"Tag Number": "PP01-364-PIT0002", "Instrument Type": "PIT", "Service Description": "Fuel Gas Pressure", "Area": "364", "IO Type": "AI"},
        {"Tag Number": "PP01-364-PDT0001", "Instrument Type": "PDT", "Service Description": "Filter Differential Pressure", "Area": "364", "IO Type": "AI"},

        # Area 364 - Flow instruments (Analog)
        {"Tag Number": "PP01-364-FIT0001", "Instrument Type": "FIT", "Service Description": "Fuel Gas Flow", "Area": "364", "IO Type": "AI"},

        # Area 364 - Level instruments (Analog)
        {"Tag Number": "PP01-364-LIT0001", "Instrument Type": "LIT", "Service Description": "Lube Oil Tank Level", "Area": "364", "IO Type": "AI"},

        # Area 361 - Digital instruments (Position switches)
        {"Tag Number": "PP01-361-ZSO0001", "Instrument Type": "ZSO", "Service Description": "MOV-001 Open Position", "Area": "361", "IO Type": "DI"},
        {"Tag Number": "PP01-361-ZSC0001", "Instrument Type": "ZSC", "Service Description": "MOV-001 Closed Position", "Area": "361", "IO Type": "DI"},
        {"Tag Number": "PP01-361-ZSO0002", "Instrument Type": "ZSO", "Service Description": "MOV-002 Open Position", "Area": "361", "IO Type": "DI"},
        {"Tag Number": "PP01-361-ZSC0002", "Instrument Type": "ZSC", "Service Description": "MOV-002 Closed Position", "Area": "361", "IO Type": "DI"},

        # Area 361 - Pressure switches (Digital)
        {"Tag Number": "PP01-361-PSH0001", "Instrument Type": "PSH", "Service Description": "High Pressure Alarm", "Area": "361", "IO Type": "DI"},
        {"Tag Number": "PP01-361-PSL0001", "Instrument Type": "PSL", "Service Description": "Low Pressure Alarm", "Area": "361", "IO Type": "DI"},

        # Area 361 - Level switches (Digital)
        {"Tag Number": "PP01-361-LSH0001", "Instrument Type": "LSH", "Service Description": "High Level Alarm", "Area": "361", "IO Type": "DI"},
        {"Tag Number": "PP01-361-LSL0001", "Instrument Type": "LSL", "Service Description": "Low Level Alarm", "Area": "361", "IO Type": "DI"},

        # Area 512 - Control valves (Analog Output)
        {"Tag Number": "PP01-512-FCV0001", "Instrument Type": "FCV", "Service Description": "Flow Control Valve", "Area": "512", "IO Type": "AO"},
        {"Tag Number": "PP01-512-PCV0001", "Instrument Type": "PCV", "Service Description": "Pressure Control Valve", "Area": "512", "IO Type": "AO"},
        {"Tag Number": "PP01-512-LCV0001", "Instrument Type": "LCV", "Service Description": "Level Control Valve", "Area": "512", "IO Type": "AO"},

        # Area 512 - Solenoid valves (Digital Output)
        {"Tag Number": "PP01-512-XV0001", "Instrument Type": "XV", "Service Description": "Isolation Valve", "Area": "512", "IO Type": "DO"},
        {"Tag Number": "PP01-512-XV0002", "Instrument Type": "XV", "Service Description": "Bypass Valve", "Area": "512", "IO Type": "DO"},
        {"Tag Number": "PP01-512-SDV0001", "Instrument Type": "SDV", "Service Description": "Emergency Shutdown Valve", "Area": "512", "IO Type": "DO"},
    ]

    # Create DataFrame
    df = pd.DataFrame(instruments)

    # Add optional columns
    df["Loop Number"] = ""
    df["P&ID Reference"] = ""
    df["Remarks"] = ""

    # Save to Excel
    output_dir = Path(__file__).parent
    output_path = output_dir / "sample_io_list.xlsx"

    df.to_excel(output_path, index=False, sheet_name="IO List")

    print(f"Created sample I/O list: {output_path}")
    print(f"Total instruments: {len(instruments)}")
    print("\nInstrument summary by area:")
    for area in df["Area"].unique():
        count = len(df[df["Area"] == area])
        print(f"  Area {area}: {count} instruments")

    return output_path


if __name__ == "__main__":
    create_sample_io_list()
