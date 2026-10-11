from typing import List, Dict, Set, Tuple
from collections import defaultdict
from app.models.domain import Signal, Cable, TQ

VALID_IO_TYPES = {"AI", "AO", "DI", "DO", "RTD", "TC"}

class DataValidator:
    def __init__(self, spare_pct: float = 10.0, max_cabinet_slots: int = 384):
        self.spare_pct = spare_pct
        self.max_cabinet_slots = max_cabinet_slots
        self.effective_cabinet_capacity = int(max_cabinet_slots * (1.0 - (spare_pct / 100.0)))

    def validate(self, signals: List[Signal], cable_sizes: Dict[str, int]) -> Tuple[List[Signal], List[TQ]]:
        """
        Validates signals, filtering invalid records and raising descriptive TQs.
        Returns (valid_signals, tqs)
        """
        tqs: List[TQ] = []
        valid_signals: List[Signal] = []

        blank_type_tags: List[str] = []
        duplicate_tags: Set[str] = set()
        seen_tags: Set[str] = set()
        pair_overflow_tags: List[str] = []

        # 1. Row-level checks
        for s in signals:
            is_valid = True

            # Blank or invalid IO type
            if not s.io_type or s.io_type.strip().upper() not in VALID_IO_TYPES:
                blank_type_tags.append(s.tag or "UNKNOWN_TAG")
                is_valid = False

            # Duplicate Tag
            if s.tag in seen_tags:
                duplicate_tags.add(s.tag)
                is_valid = False
            else:
                seen_tags.add(s.tag)

            # Pair check
            c_size = cable_sizes.get(s.cable, 24)
            if s.pair < 1 or s.pair > c_size:
                pair_overflow_tags.append(f"{s.tag} (Cable {s.cable}, Pair {s.pair} > Size {c_size})")
                is_valid = False

            if is_valid:
                valid_signals.append(s)

        if blank_type_tags:
            tqs.append(TQ(
                id="TQ-DAT-01",
                kind="data",
                items=blank_type_tags[:10],
                rule_ids=["RULE-06"],
                message=f"Missing or invalid IO type detected on {len(blank_type_tags)} signal(s). Engineering input required to assign proper CHARM module."
            ))

        if duplicate_tags:
            tqs.append(TQ(
                id="TQ-DAT-02",
                kind="data",
                items=list(duplicate_tags)[:10],
                rule_ids=["RULE-UNIQUE-TAG"],
                message=f"Duplicate instrument tag names detected on {len(duplicate_tags)} tag(s). Tags must be unique across the control system."
            ))

        if pair_overflow_tags:
            tqs.append(TQ(
                id="TQ-DAT-03",
                kind="data",
                items=pair_overflow_tags[:10],
                rule_ids=["RULE-02"],
                message=f"Pair number exceeds multi-pair cable core count on {len(pair_overflow_tags)} signal(s)."
            ))

        # 2. Cable-level A/B Contradiction Check
        cable_segs: Dict[str, Set[str]] = defaultdict(set)
        for s in valid_signals:
            if s.seg:
                cable_segs[s.cable].add(s.seg.strip().upper())

        conflicting_cables: List[str] = []
        for cbl, segs in cable_segs.items():
            if "A" in segs and "B" in segs:
                conflicting_cables.append(cbl)

        if conflicting_cables:
            tqs.append(TQ(
                id="TQ-RUL-01",
                kind="rule_conflict",
                items=conflicting_cables[:10],
                rule_ids=["RULE-01", "RULE-02"],
                message=f"Cable(s) {', '.join(conflicting_cables[:3])} carry both Train A and Train B signals simultaneously: Rule 1 (A/B Segregation) and Rule 2 (Cable Contiguity) conflict."
            ))
            # Remove conflicting cable signals from valid list so solver does not stall
            valid_signals = [s for s in valid_signals if s.cable not in conflicting_cables]

        # 3. Group Capacity Check
        group_sizes: Dict[str, int] = defaultdict(int)
        for s in valid_signals:
            if s.group:
                group_sizes[s.group] += 1

        overflow_groups = []
        for grp, count in group_sizes.items():
            if count > self.effective_cabinet_capacity:
                overflow_groups.append(f"{grp} ({count} signals > cabinet capacity {self.effective_cabinet_capacity})")

        if overflow_groups:
            tqs.append(TQ(
                id="TQ-CAP-01",
                kind="capacity",
                items=overflow_groups,
                rule_ids=["RULE-03", "RULE-04"],
                message=f"Group size exceeds single cabinet capacity limit under current {self.spare_pct}% spare margin: {', '.join(overflow_groups)}."
            ))

        return valid_signals, tqs
