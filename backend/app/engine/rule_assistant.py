import re
from typing import Optional, Dict, Any, Tuple
from app.models.rules import GenericRuleConfig

class RuleAssistant:
    """
    Natural-Language Rule Assistant.
    Parses plain-English rule drafts into typed GenericRuleConfig definitions.
    Strictly restricted to parsing rules: NEVER places signals or modifies allocations.
    """

    @staticmethod
    def parse_natural_language_rule(text: str) -> Tuple[Optional[GenericRuleConfig], str]:
        text_lower = text.lower().strip()
        
        # Determine attribute
        attr = "group"
        if any(w in text_lower for w in ["seg", "train", "train a", "train b", "safety"]):
            attr = "seg"
        elif any(w in text_lower for w in ["subtype", "sov", "solenoid", "beacon", "horn"]):
            attr = "subtype"
        elif any(w in text_lower for w in ["io type", "ai", "ao", "di", "do", "signal type"]):
            attr = "io_type"

        # Determine level
        level = "cabinet"
        if "baseplate" in text_lower or "bp" in text_lower:
            level = "baseplate"
        elif "cioc" in text_lower or "card" in text_lower:
            level = "cioc"

        # Determine relation and k_value
        relation = "same"
        k_val = 1

        if any(w in text_lower for w in ["different", "separate", "segregate", "never share"]):
            relation = "different"
        elif any(w in text_lower for w in ["at most", "max", "maximum", "limit"]):
            relation = "at_most_k"
            match = re.search(r"(\d+)", text_lower)
            if match:
                k_val = int(match.group(1))
            else:
                k_val = 2

        rule_id = f"RULE-GEN-{abs(hash(text)) % 900 + 100}"
        name = f"Assistant: {attr.capitalize()} {relation.replace('_', ' ').capitalize()} per {level.capitalize()}"

        draft = GenericRuleConfig(
            id=rule_id,
            name=name,
            enabled=True,
            relation=relation,
            attribute=attr,
            level=level,
            k_value=k_val,
            description=f"Draft compiled from: '{text}'. Configured as: {relation} {attr} per {level} (k={k_val})."
        )

        explanation = (
            f"Successfully compiled English intent into structured rule: "
            f"Relation '{relation}', Attribute '{attr}', Level '{level}'."
        )

        return draft, explanation
