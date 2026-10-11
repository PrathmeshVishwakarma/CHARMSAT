from typing import Tuple
from app.models.rules import RuleNamingPatternsConfig

class NameGenerator:
    def __init__(self, config: RuleNamingPatternsConfig):
        self.config = config

    def get_names(self, cabinet_idx: int, cioc_idx: int, baseplate_idx: int) -> Tuple[str, str, str]:
        """
        cabinet_idx: 0-indexed
        cioc_idx: 0..3
        baseplate_idx: 0..7
        Returns (cabinet_name, cioc_name, baseplate_name)
        """
        cab_num = cabinet_idx + 1
        cioc_num = cioc_idx + 1
        bp_num = baseplate_idx + 1
        
        # 1. Cabinet Name
        cab_name = self.config.cabinet_pattern.format(cab=cab_num)
        
        # 2. CIOC Number / Format representation
        if self.config.cioc_no_format == "deltav_ar1":
            cioc_no = f"AR1CIOC{cab_num:02d}{cioc_num:02d}"
        elif self.config.cioc_no_format == "numeric_3digit":
            global_cioc_num = cabinet_idx * 4 + cioc_num
            cioc_no = f"{global_cioc_num:03d}"
        else: # hierarchical
            cioc_no = f"{cab_name}-C{cioc_num:02d}"

        # 3. CIOC Name
        try:
            cioc_name = self.config.cioc_pattern.format(
                cab_name=cab_name,
                cab=cab_num,
                cioc=cioc_num,
                cioc_no=cioc_no
            )
        except Exception:
            cioc_name = f"{cab_name}-CIOC-{cioc_num:02d}"

        # 4. Baseplate Name
        try:
            baseplate_name = self.config.baseplate_pattern.format(
                cioc_name=cioc_name,
                cioc_no=cioc_no,
                bp=bp_num,
                cab_name=cab_name
            )
        except Exception:
            baseplate_name = f"{cioc_no}-CBP-{bp_num}"

        return cab_name, cioc_name, baseplate_name
