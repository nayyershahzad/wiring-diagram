"""Tests for data models."""

import pytest
from src.models import (
    Instrument,
    SignalType,
    Cable,
    CableType,
    BranchCable,
    MultipairCable,
    TerminalAllocation,
    TerminalBlock,
    TerminalStatus,
    EquipmentLocation,
    JunctionBox,
    MarshallingCabinet,
)


class TestInstrument:
    """Tests for Instrument model."""

    def test_create_instrument(self):
        """Test creating an instrument."""
        inst = Instrument(
            tag_number="PP01-364-TIT0001",
            instrument_type="TIT",
            service="Lube Oil Temperature",
            area="364"
        )
        assert inst.tag_number == "PP01-364-TIT0001"
        assert inst.instrument_type == "TIT"
        assert inst.signal_type == SignalType.ANALOG_INPUT

    def test_classify_analog_input(self):
        """Test classification of analog input instruments."""
        for inst_type in ["TIT", "PIT", "FIT", "LIT", "PDT"]:
            inst = Instrument(
                tag_number=f"PP01-364-{inst_type}0001",
                instrument_type=inst_type,
                service="Test",
                area="364"
            )
            assert inst.is_analog
            assert inst.is_input

    def test_classify_digital_input(self):
        """Test classification of digital input instruments."""
        for inst_type in ["ZS", "ZSO", "ZSC", "PSH", "PSL", "LSH", "LSL"]:
            inst = Instrument(
                tag_number=f"PP01-361-{inst_type}0001",
                instrument_type=inst_type,
                service="Test",
                area="361"
            )
            assert inst.is_digital
            assert inst.is_input

    def test_classify_analog_output(self):
        """Test classification of analog output instruments."""
        for inst_type in ["FCV", "PCV", "LCV", "TY"]:
            inst = Instrument(
                tag_number=f"PP01-512-{inst_type}0001",
                instrument_type=inst_type,
                service="Test",
                area="512"
            )
            assert inst.is_analog
            assert inst.is_output

    def test_classify_digital_output(self):
        """Test classification of digital output instruments."""
        for inst_type in ["XV", "XY", "SOV", "SDV"]:
            inst = Instrument(
                tag_number=f"PP01-512-{inst_type}0001",
                instrument_type=inst_type,
                service="Test",
                area="512"
            )
            assert inst.is_digital
            assert inst.is_output


class TestCable:
    """Tests for Cable models."""

    def test_create_branch_cable(self):
        """Test creating a branch cable."""
        cable = BranchCable(
            tag_number="PP01-364-TIT0001",
            cable_type=CableType.BRANCH,
            specification="1Px1.5mm2",
            pair_count=1,
            from_location="PP01-364-TIT0001",
            to_location="PP01-601-IAJB0001",
            instrument_tag="PP01-364-TIT0001"
        )
        assert cable.is_branch
        assert not cable.is_multipair

    def test_create_multipair_cable(self):
        """Test creating a multipair cable."""
        cable = MultipairCable(
            tag_number="PP01-601-I0001",
            cable_type=CableType.MULTIPAIR,
            specification="5PRx1.0mm2",
            pair_count=5,
            from_location="PP01-601-IAJB0001",
            to_location="PP01-601-ICP001",
            used_pairs=4,
            spare_pairs=1,
        )
        assert cable.is_multipair
        assert cable.utilization_percent == 80.0
        assert cable.spare_percent == 20.0


class TestTerminal:
    """Tests for Terminal models."""

    def test_create_terminal_allocation(self):
        """Test creating a terminal allocation."""
        alloc = TerminalAllocation(
            terminal_number=1,
            terminal_positive="1+",
            terminal_negative="1-",
            terminal_shield="1S",
            instrument_tag="PP01-364-TIT0001",
            status=TerminalStatus.USED,
        )
        assert alloc.is_used
        assert not alloc.is_spare

    def test_terminal_block_counts(self):
        """Test terminal block counting."""
        allocations = [
            TerminalAllocation(
                terminal_number=i,
                terminal_positive=f"{i}+",
                terminal_negative=f"{i}-",
                instrument_tag=f"INST{i}" if i <= 4 else "SPARE",
                status=TerminalStatus.USED if i <= 4 else TerminalStatus.SPARE,
            )
            for i in range(1, 6)
        ]

        tb = TerminalBlock(
            tag_number="TB601-I0001",
            location=EquipmentLocation.JUNCTION_BOX,
            parent_equipment="PP01-601-IAJB0001",
            total_terminals=5,
            allocations=allocations,
        )

        assert tb.used_terminals == 4
        assert tb.spare_terminals == 1
        assert tb.utilization_percent == 80.0


class TestJunctionBox:
    """Tests for JunctionBox model."""

    def test_create_junction_box(self):
        """Test creating a junction box."""
        jb = JunctionBox(
            tag_number="PP01-601-IAJB0001",
            jb_type="ANALOG",
            area="601",
        )
        assert jb.is_analog
        assert not jb.is_digital
