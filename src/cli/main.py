"""Command-line interface for DCS Interconnection Diagram Generator."""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """DCS Interconnection Diagram Generator.

    Generate professional DCS interconnection diagrams from I/O lists.
    """
    pass


@cli.command()
@click.option(
    "--io-list", "-i",
    required=True,
    type=click.Path(exists=True),
    help="Path to the Excel I/O list file"
)
@click.option(
    "--jb-tag", "-j",
    required=True,
    help="Junction box tag (e.g., PP01-601-IAJB0002)"
)
@click.option(
    "--cabinet-tag", "-c",
    required=True,
    help="Marshalling cabinet tag (e.g., PP01-601-ICP001)"
)
@click.option(
    "--output", "-o",
    required=True,
    type=click.Path(),
    help="Output PDF file path"
)
@click.option(
    "--area", "-a",
    default=None,
    help="Filter by area code (optional)"
)
@click.option(
    "--spare-percent",
    default=0.20,
    type=float,
    help="Spare terminal percentage (default: 0.20)"
)
@click.option(
    "--drawing-number", "-d",
    default="DWG-001",
    help="Drawing number"
)
@click.option(
    "--title", "-t",
    default=None,
    help="Drawing title (default: auto-generated)"
)
def generate(io_list, jb_tag, cabinet_tag, output, area, spare_percent, drawing_number, title):
    """Generate interconnection diagram from I/O list."""
    from ..parsers import load_io_list, filter_instruments_by_area
    from ..engine import TagGenerator, classify_jb_type
    from ..drawing import render_interconnection_diagram

    console.print(Panel.fit(
        "[bold blue]DCS Interconnection Diagram Generator[/bold blue]",
        border_style="blue"
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Load I/O list
        task = progress.add_task("Loading I/O list...", total=None)
        result = load_io_list(io_list)

        if not result.is_valid:
            console.print("[red]Error loading I/O list:[/red]")
            for error in result.validation_result.errors:
                console.print(f"  - {error.message}")
            return

        instruments = result.instruments
        progress.update(task, description=f"Loaded {len(instruments)} instruments")

        # Filter by area if specified
        if area:
            instruments = filter_instruments_by_area(instruments, area)
            console.print(f"Filtered to {len(instruments)} instruments in area {area}")

        if not instruments:
            console.print("[red]No instruments found after filtering[/red]")
            return

        # Classify JB type
        jb_type = classify_jb_type(instruments)
        console.print(f"JB Type: [cyan]{jb_type.value}[/cyan]")

        # Generate tags
        tag_gen = TagGenerator()
        multipair_cable_tag = tag_gen.generate_multipair_cable_tag()
        tb_tag = tag_gen.generate_terminal_block_tag(multipair_cable_tag)

        # Auto-generate title if not provided
        if title is None:
            title = f"{jb_tag} ({jb_type.value} JB)"

        # Generate diagram
        progress.update(task, description="Generating diagram...")

        try:
            output_path = render_interconnection_diagram(
                instruments=instruments,
                jb_tag=jb_tag,
                cabinet_tag=cabinet_tag,
                multipair_cable_tag=multipair_cable_tag,
                tb_tag=tb_tag,
                output_path=output,
                drawing_number=drawing_number,
                title=title,
                spare_percent=spare_percent,
            )

            progress.update(task, description="Complete!")
            console.print(f"\n[green]✓ Generated diagram:[/green] {output_path}")

        except Exception as e:
            console.print(f"[red]Error generating diagram: {e}[/red]")
            raise


@cli.command()
@click.option(
    "--io-list", "-i",
    required=True,
    type=click.Path(exists=True),
    help="Path to the Excel I/O list file"
)
def validate(io_list):
    """Validate an I/O list file."""
    from ..parsers import load_io_list

    console.print(f"Validating: [cyan]{io_list}[/cyan]\n")

    result = load_io_list(io_list)

    if result.is_valid:
        console.print(f"[green]✓ Valid I/O list with {result.instrument_count} instruments[/green]")
    else:
        console.print("[red]✗ Validation errors found:[/red]")
        for error in result.validation_result.errors:
            console.print(f"  Row {error.row}: {error.message}")

    if result.validation_result.warnings:
        console.print("\n[yellow]Warnings:[/yellow]")
        for warning in result.validation_result.warnings:
            console.print(f"  Row {warning.row}: {warning.message}")

    # Show summary table
    if result.instruments:
        table = Table(title="Instrument Summary")
        table.add_column("Area", style="cyan")
        table.add_column("Count", justify="right")

        from ..parsers import group_instruments_by_area
        groups = group_instruments_by_area(result.instruments)

        for area, insts in sorted(groups.items()):
            table.add_row(area, str(len(insts)))

        console.print(table)


@cli.command()
@click.option(
    "--io-list", "-i",
    required=True,
    type=click.Path(exists=True),
    help="Path to the Excel I/O list file"
)
@click.option(
    "--output", "-o",
    required=True,
    type=click.Path(),
    help="Output Excel file path"
)
@click.option(
    "--spare-percent",
    default=0.20,
    type=float,
    help="Spare percentage (default: 0.20)"
)
def cable_schedule(io_list, output, spare_percent):
    """Generate cable schedule from I/O list."""
    import pandas as pd
    from ..parsers import load_io_list, group_instruments_by_area
    from ..engine import size_cables_for_jb, TagGenerator

    console.print("Generating cable schedule...\n")

    result = load_io_list(io_list)
    if not result.is_valid:
        console.print("[red]Error loading I/O list[/red]")
        return

    groups = group_instruments_by_area(result.instruments)

    cable_data = []
    tag_gen = TagGenerator()

    for area, instruments in sorted(groups.items()):
        # Generate JB and cable tags
        from ..engine import classify_jb_type
        jb_type = classify_jb_type(instruments)
        jb_tag = tag_gen.generate_jb_tag(jb_type)
        cable_tag = tag_gen.generate_multipair_cable_tag()

        # Size cables
        sizing = size_cables_for_jb(
            instruments=instruments,
            jb_tag=jb_tag,
            cabinet_tag="TBD",
            multipair_cable_tag=cable_tag,
            spare_percent=spare_percent,
        )

        # Add branch cables
        for bc in sizing.branch_cables:
            cable_data.append({
                "Cable Tag": bc.tag_number,
                "Type": "BRANCH",
                "Specification": bc.specification,
                "From": bc.from_location,
                "To": bc.to_location,
                "Pairs": bc.pair_count,
            })

        # Add multipair cable
        mp = sizing.multipair_cable
        cable_data.append({
            "Cable Tag": mp.tag_number,
            "Type": "MULTIPAIR",
            "Specification": mp.specification,
            "From": mp.from_location,
            "To": mp.to_location,
            "Pairs": mp.pair_count,
            "Used": mp.used_pairs,
            "Spare": mp.spare_pairs,
        })

    # Export to Excel
    df = pd.DataFrame(cable_data)
    df.to_excel(output, index=False)

    console.print(f"[green]✓ Cable schedule saved to: {output}[/green]")
    console.print(f"  Total cables: {len(cable_data)}")


@cli.command()
def interactive():
    """Run interactive mode for diagram generation."""
    from ..parsers import load_io_list, filter_instruments_by_area, group_instruments_by_area
    from ..engine import classify_jb_type, TagGenerator, suggest_jb_count
    from ..drawing import render_interconnection_diagram

    console.print(Panel.fit(
        "[bold blue]DCS Interconnection Diagram Generator[/bold blue]\n"
        "[dim]Interactive Mode[/dim]",
        border_style="blue"
    ))

    # Step 1: Load I/O List
    console.print("\n[bold]Step 1: Load I/O List[/bold]")
    io_list_path = console.input("Enter path to I/O list Excel file: ")

    if not Path(io_list_path).exists():
        console.print(f"[red]File not found: {io_list_path}[/red]")
        return

    result = load_io_list(io_list_path)
    if not result.is_valid:
        console.print("[red]Error loading I/O list[/red]")
        for error in result.validation_result.errors:
            console.print(f"  - {error.message}")
        return

    console.print(f"[green]✓ Loaded {result.instrument_count} instruments[/green]")

    # Step 2: Select instruments
    console.print("\n[bold]Step 2: Select Instruments[/bold]")

    groups = group_instruments_by_area(result.instruments)
    console.print("Available areas:")
    for area, insts in sorted(groups.items()):
        console.print(f"  {area}: {len(insts)} instruments")

    area_filter = console.input("Filter by area (or 'all'): ").strip()

    if area_filter.lower() == 'all':
        instruments = result.instruments
    else:
        instruments = filter_instruments_by_area(result.instruments, area_filter)

    if not instruments:
        console.print("[red]No instruments found[/red]")
        return

    console.print(f"[green]✓ Selected {len(instruments)} instruments[/green]")

    # Suggest JB configuration
    jb_suggestion = suggest_jb_count(instruments)
    console.print(f"\n[cyan]Suggested configuration:[/cyan]")
    console.print(f"  Analog JBs needed: {jb_suggestion['analog_jbs']}")
    console.print(f"  Digital JBs needed: {jb_suggestion['digital_jbs']}")

    # Step 3: Configure JB
    console.print("\n[bold]Step 3: Configure Junction Box[/bold]")
    jb_tag = console.input("Enter JB tag number: ").strip()

    jb_type = classify_jb_type(instruments)
    console.print(f"JB Type detected: [cyan]{jb_type.value}[/cyan]")

    # Step 4: Configure Cabinet
    console.print("\n[bold]Step 4: Configure Cabinet[/bold]")
    cabinet_tag = console.input("Enter Cabinet tag: ").strip()

    tag_gen = TagGenerator()
    multipair_cable_tag = tag_gen.generate_multipair_cable_tag()
    tb_tag = tag_gen.generate_terminal_block_tag(multipair_cable_tag)

    console.print(f"Generated multipair cable tag: [cyan]{multipair_cable_tag}[/cyan]")
    console.print(f"Generated TB tag: [cyan]{tb_tag}[/cyan]")

    # Step 5: Generate
    console.print("\n[bold]Step 5: Generate Drawing[/bold]")
    output_file = console.input("Output filename: ").strip()

    if not output_file.endswith('.pdf'):
        output_file += '.pdf'

    # Ensure output directory exists
    output_path = Path("examples/output") / output_file
    output_path.parent.mkdir(parents=True, exist_ok=True)

    title = f"{jb_tag} ({jb_type.value} JB)"

    try:
        render_interconnection_diagram(
            instruments=instruments,
            jb_tag=jb_tag,
            cabinet_tag=cabinet_tag,
            multipair_cable_tag=multipair_cable_tag,
            tb_tag=tb_tag,
            output_path=str(output_path),
            drawing_number="DWG-001",
            title=title,
        )

        console.print(f"\n[green]✓ Generated interconnection diagram[/green]")
        console.print(f"[green]✓ Saved to: {output_path}[/green]")

    except Exception as e:
        console.print(f"[red]Error generating diagram: {e}[/red]")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
