"""LLM-powered rules parsing service using Claude API."""

import os
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import anthropic


@dataclass
class AllocationRules:
    """Parsed allocation rules from natural language input."""

    # Spare capacity rules
    spare_percent: float = 0.20  # Default 20%
    spare_per_card_min: Optional[int] = None  # Minimum spare channels per card

    # Segregation rules
    segregate_by_area: bool = False  # Keep different areas on separate cards
    segregate_by_service: bool = False  # Keep different services separate
    segregate_is_non_is: bool = True  # IS and non-IS on separate cards
    segregate_sil_levels: bool = True  # Different SIL levels on separate cards

    # Cabinet constraints
    max_cabinets_per_area: Optional[int] = None  # Max cabinets for an area
    max_cards_per_cabinet: Optional[int] = None  # Max I/O cards per cabinet

    # Card constraints
    max_channels_used_percent: float = 0.80  # Max utilization (leaving room for spare)
    prefer_full_cards: bool = False  # Fill cards completely before using new ones

    # Location rules
    area_to_location_mapping: Dict[str, str] = field(default_factory=dict)  # Area -> Cabinet location

    # Custom groupings
    group_by_loop: bool = False  # Keep same loop on same card
    group_by_unit: bool = False  # Keep same unit on same card

    # Additional custom rules (free-form)
    custom_rules: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'spare_percent': self.spare_percent,
            'spare_per_card_min': self.spare_per_card_min,
            'segregate_by_area': self.segregate_by_area,
            'segregate_by_service': self.segregate_by_service,
            'segregate_is_non_is': self.segregate_is_non_is,
            'segregate_sil_levels': self.segregate_sil_levels,
            'max_cabinets_per_area': self.max_cabinets_per_area,
            'max_cards_per_cabinet': self.max_cards_per_cabinet,
            'max_channels_used_percent': self.max_channels_used_percent,
            'prefer_full_cards': self.prefer_full_cards,
            'area_to_location_mapping': self.area_to_location_mapping,
            'group_by_loop': self.group_by_loop,
            'group_by_unit': self.group_by_unit,
            'custom_rules': self.custom_rules,
        }


class LLMRulesService:
    """Service to parse natural language allocation rules using Claude."""

    SYSTEM_PROMPT = """You are an expert I/O allocation rules parser for industrial control systems (DCS/SIS/RTU).

Your task is to extract structured allocation rules from natural language input provided by engineers.

The user may specify rules about:
1. **Spare Capacity**: Percentage of spare channels (e.g., "20% spare", "25% spare capacity", "at least 2 spare channels per card")
2. **Segregation**: Keeping certain signals separate (e.g., "separate areas", "IS and non-IS separate", "different SIL levels on different cards")
3. **Cabinet Constraints**: Physical limitations (e.g., "max 2 cabinets for area 364", "no more than 10 cards per cabinet")
4. **Card Utilization**: How to fill cards (e.g., "maximize card usage", "keep 20% spare per card")
5. **Location Mapping**: Where to place equipment (e.g., "area 364 goes to CCR-1", "RTU signals to remote cabinet")
6. **Grouping**: How to group signals (e.g., "keep same loop together", "group by unit")

You must respond with a valid JSON object containing these fields:
{
    "spare_percent": <float 0.0-1.0, default 0.20>,
    "spare_per_card_min": <int or null>,
    "segregate_by_area": <bool>,
    "segregate_by_service": <bool>,
    "segregate_is_non_is": <bool>,
    "segregate_sil_levels": <bool>,
    "max_cabinets_per_area": <int or null>,
    "max_cards_per_cabinet": <int or null>,
    "max_channels_used_percent": <float 0.0-1.0>,
    "prefer_full_cards": <bool>,
    "area_to_location_mapping": {<area>: <location>},
    "group_by_loop": <bool>,
    "group_by_unit": <bool>,
    "custom_rules": [<list of rules that don't fit above categories>],
    "interpretation": "<brief explanation of what you understood>"
}

If a rule is not mentioned, use sensible defaults. Always include the "interpretation" field explaining your understanding."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the service with Claude API key."""
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not provided or found in environment")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"  # Using Sonnet for cost efficiency

    def parse_rules(self, user_input: str) -> AllocationRules:
        """
        Parse natural language rules into structured AllocationRules.

        Args:
            user_input: Natural language description of allocation rules

        Returns:
            AllocationRules object with parsed rules
        """
        if not user_input or not user_input.strip():
            return AllocationRules()  # Return defaults

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Parse the following I/O allocation rules:\n\n{user_input}"
                    }
                ]
            )

            # Extract the response text
            response_text = message.content[0].text

            # Parse JSON from response
            # Handle case where response might have markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            parsed = json.loads(response_text)

            # Convert to AllocationRules
            rules = AllocationRules(
                spare_percent=parsed.get('spare_percent', 0.20),
                spare_per_card_min=parsed.get('spare_per_card_min'),
                segregate_by_area=parsed.get('segregate_by_area', False),
                segregate_by_service=parsed.get('segregate_by_service', False),
                segregate_is_non_is=parsed.get('segregate_is_non_is', True),
                segregate_sil_levels=parsed.get('segregate_sil_levels', True),
                max_cabinets_per_area=parsed.get('max_cabinets_per_area'),
                max_cards_per_cabinet=parsed.get('max_cards_per_cabinet'),
                max_channels_used_percent=parsed.get('max_channels_used_percent', 0.80),
                prefer_full_cards=parsed.get('prefer_full_cards', False),
                area_to_location_mapping=parsed.get('area_to_location_mapping', {}),
                group_by_loop=parsed.get('group_by_loop', False),
                group_by_unit=parsed.get('group_by_unit', False),
                custom_rules=parsed.get('custom_rules', []),
            )

            # Store interpretation for display
            rules._interpretation = parsed.get('interpretation', '')

            return rules

        except anthropic.APIError as e:
            print(f"Claude API error: {e}")
            return AllocationRules()  # Return defaults on error
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            return AllocationRules()
        except Exception as e:
            print(f"Unexpected error parsing rules: {e}")
            return AllocationRules()

    def get_rule_suggestions(self, instrument_summary: Dict[str, Any]) -> str:
        """
        Get AI-generated rule suggestions based on instrument data.

        Args:
            instrument_summary: Summary of instruments (counts by type, areas, etc.)

        Returns:
            Natural language suggestions for allocation rules
        """
        try:
            prompt = f"""Based on this I/O allocation summary, suggest optimal allocation rules:

Instrument Summary:
- Total Instruments: {instrument_summary.get('total', 0)}
- DCS Signals: AI={instrument_summary.get('dcs_ai', 0)}, AO={instrument_summary.get('dcs_ao', 0)}, DI={instrument_summary.get('dcs_di', 0)}, DO={instrument_summary.get('dcs_do', 0)}
- SIS Signals: AI={instrument_summary.get('sis_ai', 0)}, AO={instrument_summary.get('sis_ao', 0)}, DI={instrument_summary.get('sis_di', 0)}, DO={instrument_summary.get('sis_do', 0)}
- Areas: {instrument_summary.get('areas', [])}

Provide 3-5 concise rule suggestions that would optimize the I/O card allocation for this project. Focus on practical engineering considerations like:
- Appropriate spare capacity
- Segregation requirements
- Cabinet organization
- Any constraints based on the signal distribution

Keep suggestions brief and actionable."""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return message.content[0].text

        except Exception as e:
            print(f"Error getting suggestions: {e}")
            return ""


def parse_allocation_rules(
    user_input: str,
    api_key: Optional[str] = None
) -> AllocationRules:
    """
    Convenience function to parse allocation rules.

    Args:
        user_input: Natural language rules description
        api_key: Optional Claude API key

    Returns:
        AllocationRules object
    """
    service = LLMRulesService(api_key=api_key)
    return service.parse_rules(user_input)
