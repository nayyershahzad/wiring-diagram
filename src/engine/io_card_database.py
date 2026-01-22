"""I/O Card database loader from YAML specifications."""

import yaml
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from ..models.io_card import IOModule, IOType, ControlSystem, SILRating


@dataclass
class VendorSpec:
    """Vendor I/O module specifications."""
    vendor: str
    control_systems: Dict  # DCS, SIS, RTU configurations
    modules: Dict[str, List[IOModule]]  # Categorized by system
    channel_density: Dict[str, Dict[str, int]]  # {DCS: {AI: 8, AO: 8}, SIS: {...}}


class IOCardDatabase:
    """Database of I/O card specifications loaded from YAML."""

    def __init__(self, spec_path: Optional[str] = None):
        """
        Initialize the database.

        Args:
            spec_path: Path to YAML spec file. Defaults to yokogawa_io_allocation_spec.yaml
        """
        self.spec_path = spec_path or self._get_default_spec_path()
        self.vendors: Dict[str, VendorSpec] = {}
        self._load_specifications()

    def _get_default_spec_path(self) -> str:
        """Get default path to Yokogawa spec."""
        return str(Path(__file__).parent.parent.parent / "specs" / "yokogawa_io_allocation_spec.yaml")

    def _load_specifications(self):
        """Load all vendor specifications."""
        self._load_yokogawa_spec()

    def _load_yokogawa_spec(self):
        """Load Yokogawa I/O module specifications from YAML."""
        try:
            with open(self.spec_path, 'r') as f:
                spec = yaml.safe_load(f)
        except FileNotFoundError:
            # Use hardcoded defaults if YAML not found
            self._load_default_yokogawa()
            return

        modules = {}
        channel_density = {}

        # Parse DCS modules
        if 'control_systems' in spec and 'DCS' in spec['control_systems']:
            dcs_config = spec['control_systems']['DCS']
            modules['DCS'] = self._parse_io_modules(
                dcs_config.get('io_modules', {}),
                ControlSystem.DCS
            )

        # Parse SIS/ESD modules
        if 'control_systems' in spec and 'ESD' in spec['control_systems']:
            sis_config = spec['control_systems']['ESD']
            modules['SIS'] = self._parse_io_modules(
                sis_config.get('io_modules', {}),
                ControlSystem.SIS
            )

        # Parse RTU modules
        if 'control_systems' in spec and 'RTU' in spec['control_systems']:
            rtu_config = spec['control_systems']['RTU']
            modules['RTU'] = self._parse_io_modules(
                rtu_config.get('io_modules', {}),
                ControlSystem.RTU
            )

        # Load channel density
        if 'io_allocation' in spec and 'channel_density' in spec['io_allocation']:
            channel_density = spec['io_allocation']['channel_density']

        self.vendors['Yokogawa'] = VendorSpec(
            vendor='Yokogawa',
            control_systems=spec.get('control_systems', {}),
            modules=modules,
            channel_density=channel_density
        )

    def _load_default_yokogawa(self):
        """Load hardcoded default Yokogawa modules."""
        modules = {
            'DCS': [
                IOModule("AAI143-H00", IOType.AI, 8, "4-20mA", ["HART"], None, ControlSystem.DCS),
                IOModule("AAO143-H00", IOType.AO, 8, "4-20mA", ["HART"], None, ControlSystem.DCS),
                IOModule("ADV151-P00", IOType.DI, 32, "24VDC", [], None, ControlSystem.DCS),
                IOModule("ADV159-P00", IOType.DO, 32, "24VDC", [], None, ControlSystem.DCS),
            ],
            'SIS': [
                IOModule("ATI4D-00", IOType.AI, 8, "4-20mA", ["SIL3"], SILRating.SIL3, ControlSystem.SIS),
                IOModule("ATO4D-00", IOType.AO, 4, "4-20mA", ["SIL3"], SILRating.SIL3, ControlSystem.SIS),
                IOModule("ADI4D-00", IOType.DI, 16, "24VDC", ["SIL3"], SILRating.SIL3, ControlSystem.SIS),
                IOModule("ADO4D-00", IOType.DO, 8, "24VDC", ["SIL3"], SILRating.SIL3, ControlSystem.SIS),
            ],
            'RTU': [
                IOModule("F3AD04-5N", IOType.AI, 4, "4-20mA", [], None, ControlSystem.RTU),
                IOModule("F3DA04-6N", IOType.AO, 4, "4-20mA", [], None, ControlSystem.RTU),
                IOModule("F3XD32-3N", IOType.DI, 32, "24VDC", [], None, ControlSystem.RTU),
                IOModule("F3YD32-1N", IOType.DO, 32, "24VDC", [], None, ControlSystem.RTU),
            ]
        }

        channel_density = {
            'DCS': {'AI': 8, 'AO': 8, 'DI': 32, 'DO': 32},
            'SIS': {'AI': 8, 'AO': 4, 'DI': 16, 'DO': 8},
            'RTU': {'AI': 4, 'AO': 4, 'DI': 32, 'DO': 32}
        }

        self.vendors['Yokogawa'] = VendorSpec(
            vendor='Yokogawa',
            control_systems={},
            modules=modules,
            channel_density=channel_density
        )

    def _parse_io_modules(
        self,
        io_modules: Dict,
        system: ControlSystem
    ) -> List[IOModule]:
        """Parse I/O modules from YAML structure."""
        modules = []

        type_mapping = {
            'analog_input': IOType.AI,
            'analog_output': IOType.AO,
            'digital_input': IOType.DI,
            'digital_output': IOType.DO,
            'rtd_thermocouple': IOType.AI,  # Treat as AI
        }

        for type_key, module_list in io_modules.items():
            if not module_list:
                continue

            io_type = type_mapping.get(type_key, IOType.AI)

            for mod_spec in module_list:
                sil_rating = None
                if mod_spec.get('sil_rating'):
                    sil_rating = SILRating(mod_spec['sil_rating'])

                module = IOModule(
                    model=mod_spec['model'],
                    io_type=io_type,
                    channels=mod_spec['channels'],
                    signal_type=mod_spec['signal_type'],
                    features=mod_spec.get('features', []),
                    sil_rating=sil_rating,
                    control_system=system,
                    vendor='Yokogawa'
                )
                modules.append(module)

        return modules

    def get_module(
        self,
        vendor: str,
        system: ControlSystem,
        io_type: IOType,
        sil_required: bool = False
    ) -> Optional[IOModule]:
        """
        Get the most appropriate module for given requirements.

        Args:
            vendor: Vendor name (e.g., "Yokogawa")
            system: Control system (DCS, SIS, RTU)
            io_type: I/O type (AI, AO, DI, DO)
            sil_required: Whether SIL rating is required

        Returns:
            IOModule or None if not found
        """
        if vendor not in self.vendors:
            return None

        spec = self.vendors[vendor]
        system_key = system.value

        if system_key not in spec.modules:
            return None

        # Find matching modules
        candidates = [
            m for m in spec.modules[system_key]
            if m.io_type == io_type
        ]

        if sil_required:
            candidates = [m for m in candidates if m.is_safety_rated]

        # Return first match (primary/default module)
        return candidates[0] if candidates else None

    def get_all_modules(
        self,
        vendor: str,
        system: ControlSystem,
        io_type: IOType
    ) -> List[IOModule]:
        """
        Get all modules matching the criteria.

        Args:
            vendor: Vendor name
            system: Control system
            io_type: I/O type

        Returns:
            List of matching IOModule objects
        """
        if vendor not in self.vendors:
            return []

        spec = self.vendors[vendor]
        system_key = system.value

        if system_key not in spec.modules:
            return []

        return [
            m for m in spec.modules[system_key]
            if m.io_type == io_type
        ]

    def get_channel_density(
        self,
        vendor: str,
        system: ControlSystem,
        io_type: IOType
    ) -> int:
        """
        Get channel density for a given configuration.

        Args:
            vendor: Vendor name
            system: Control system
            io_type: I/O type

        Returns:
            Number of channels per card (default 8)
        """
        if vendor not in self.vendors:
            return 8  # Default

        spec = self.vendors[vendor]
        system_key = system.value
        io_key = io_type.value

        if system_key in spec.channel_density:
            return spec.channel_density[system_key].get(io_key, 8)

        return 8  # Default

    def get_available_vendors(self) -> List[str]:
        """Get list of available vendors."""
        return list(self.vendors.keys())

    def is_vendor_supported(self, vendor: str) -> bool:
        """Check if vendor is supported."""
        return vendor in self.vendors


# Global database instance (singleton pattern)
_db_instance: Optional[IOCardDatabase] = None


def get_io_card_database() -> IOCardDatabase:
    """Get or create the global IOCardDatabase instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = IOCardDatabase()
    return _db_instance
