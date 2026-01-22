"""Tests for processing engine."""

import pytest
from src.models import Instrument, SignalType
from src.engine import (
    classify_instrument,
    classify_jb_type,
    JBType,
    calculate_multipair_size,
    get_branch_cable_spec,
    allocate_jb_terminals,
    allocate_cabinet_terminals,
    TagGenerator,
)


class TestClassifier:
    """Tests for instrument classifier."""

    def test_classify_tit_as_analog_input(self):
        """Test TIT classification."""
        result = classify_instrument("TIT")
        assert result == SignalType.ANALOG_INPUT

    def test_classify_zs_as_digital_input(self):
        """Test ZS classification."""
        result = classify_instrument("ZS")
        assert result == SignalType.DIGITAL_INPUT

    def test_classify_jb_type_analog(self):
        """Test JB type classification for analog instruments."""
        instruments = [
            Instrument("PP01-364-TIT0001", "TIT", "Test", "364"),
            Instrument("PP01-364-PIT0001", "PIT", "Test", "364"),
        ]
        result = classify_jb_type(instruments)
        assert result == JBType.ANALOG

    def test_classify_jb_type_digital(self):
        """Test JB type classification for digital instruments."""
        instruments = [
            Instrument("PP01-361-ZS0001", "ZS", "Test", "361"),
            Instrument("PP01-361-PSH0001", "PSH", "Test", "361"),
        ]
        result = classify_jb_type(instruments)
        assert result == JBType.DIGITAL

    def test_classify_jb_type_mixed(self):
        """Test JB type classification for mixed instruments."""
        instruments = [
            Instrument("PP01-364-TIT0001", "TIT", "Test", "364"),
            Instrument("PP01-361-ZS0001", "ZS", "Test", "361"),
        ]
        result = classify_jb_type(instruments)
        assert result == JBType.MIXED


class TestCableSizer:
    """Tests for cable sizing engine."""

    def test_multipair_sizing_4_instruments(self):
        """Test multipair sizing for 4 instruments."""
        result = calculate_multipair_size(4)
        assert result == 5  # 4 + 20% = 4.8, rounds to 5

    def test_multipair_sizing_5_instruments(self):
        """Test multipair sizing for 5 instruments."""
        result = calculate_multipair_size(5)
        assert result == 10  # 5 + 20% = 6, needs 10PR

    def test_multipair_sizing_16_instruments(self):
        """Test multipair sizing for 16 instruments."""
        result = calculate_multipair_size(16)
        assert result == 20  # 16 + 20% = 19.2, needs 20PR

    def test_branch_cable_spec_analog(self):
        """Test branch cable spec for analog instruments."""
        spec, pairs = get_branch_cable_spec(SignalType.ANALOG_INPUT)
        assert spec == "1Px1.5mm2"
        assert pairs == 1

    def test_branch_cable_spec_rtd_4wire(self):
        """Test branch cable spec for 4-wire RTD."""
        spec, pairs = get_branch_cable_spec(SignalType.RTD_4WIRE)
        assert spec == "2Px1.5mm2"
        assert pairs == 2


class TestTerminalAllocator:
    """Tests for terminal allocation engine."""

    def test_allocate_jb_terminals(self):
        """Test JB terminal allocation."""
        instruments = [
            Instrument(f"PP01-364-TIT000{i}", "TIT", "Test", "364")
            for i in range(1, 5)
        ]

        result = allocate_jb_terminals(instruments, "PP01-601-IAJB0001")

        assert result.used_count == 4
        assert result.spare_count == 1  # 20% of 4 = 0.8, rounds up to 1
        assert result.total_count == 5

    def test_allocate_cabinet_terminals(self):
        """Test cabinet terminal allocation."""
        instruments = [
            Instrument(f"PP01-364-TIT000{i}", "TIT", "Test", "364")
            for i in range(1, 5)
        ]

        result = allocate_cabinet_terminals(
            instruments,
            "PP01-601-ICP001",
            "TB601-I0001"
        )

        assert result.used_count == 4
        assert result.spare_count == 1
        assert result.spare_percent == 20.0


class TestTagGenerator:
    """Tests for tag generator."""

    def test_generate_jb_tag_analog(self):
        """Test analog JB tag generation."""
        gen = TagGenerator()
        tag = gen.generate_jb_tag(JBType.ANALOG)
        assert tag == "PP01-601-IAJB0001"

    def test_generate_jb_tag_digital(self):
        """Test digital JB tag generation."""
        gen = TagGenerator()
        tag = gen.generate_jb_tag(JBType.DIGITAL)
        assert tag == "PP01-601-IDJB0001"

    def test_generate_multipair_cable_tag(self):
        """Test multipair cable tag generation."""
        gen = TagGenerator()
        tag = gen.generate_multipair_cable_tag()
        assert tag == "PP01-601-I0001"

    def test_generate_tb_tag(self):
        """Test terminal block tag generation."""
        gen = TagGenerator()
        cable_tag = "PP01-601-I0004"
        tb_tag = gen.generate_terminal_block_tag(cable_tag)
        assert tb_tag == "TB601-I0004"

    def test_sequential_tag_generation(self):
        """Test sequential tag generation."""
        gen = TagGenerator()

        tag1 = gen.generate_multipair_cable_tag()
        tag2 = gen.generate_multipair_cable_tag()
        tag3 = gen.generate_multipair_cable_tag()

        assert tag1 == "PP01-601-I0001"
        assert tag2 == "PP01-601-I0002"
        assert tag3 == "PP01-601-I0003"
