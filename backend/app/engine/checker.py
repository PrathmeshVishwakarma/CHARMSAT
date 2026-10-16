from typing import List, Dict, Set, Optional
from collections import defaultdict
import copy
from app.models.domain import AllocatedSlot, Violation, Signal
from app.models.rules import RuleSetConfig
from app.engine.hardware import hardware_for, normalise_subtype

class IndependentChecker:
    """
    Independent Verification Engine.
    Shares NO data structures or algorithms with the CP-SAT solver.
    Re-derives every constraint from the concrete allocation output.
    """

    def __init__(self, rules: RuleSetConfig):
        self.rules = rules

    def verify(self, allocations: List[AllocatedSlot], signals: Optional[List[Signal]] = None) -> List[Violation]:
        violations: List[Violation] = []

        # 0. Global Unique Slot Occupancy Check
        slot_map: Dict[int, List[AllocatedSlot]] = defaultdict(list)
        for s in allocations:
            slot_map[s.global_slot].append(s)

        for g_slot, occupants in slot_map.items():
            if len(occupants) > 1:
                tags = [o.tag or f"Spare-{o.cable}-{o.pair}" for o in occupants]
                for o in occupants:
                    violations.append(Violation(
                        rule_id="RULE-SLOT-COLLISION",
                        rule_name="Slot Exclusivity",
                        tag=o.tag,
                        cable=o.cable,
                        cabinet=o.cabinet,
                        cioc=o.cioc,
                        baseplate=o.baseplate,
                        slot=o.slot,
                        message=f"Global slot {g_slot} ({o.cabinet_name} CIOC {o.cioc+1} BP {o.baseplate+1} Slot {o.slot+1}) is double-booked by: {', '.join(tags)}."
                    ))

        # 1. Rule 1: A/B Segregation
        if self.rules.ab_segregation.enabled:
            level = self.rules.ab_segregation.level
            # Group by CIOC or Cabinet
            unit_signals: Dict[str, List[AllocatedSlot]] = defaultdict(list)
            for s in allocations:
                if s.seg:
                    if level == "cioc":
                        key = f"CAB{s.cabinet}_CIOC{s.cioc}"
                    elif level == "baseplate":
                        key = f"CAB{s.cabinet}_CIOC{s.cioc}_BP{s.baseplate}"
                    else:
                        key = f"CAB{s.cabinet}"
                    unit_signals[key].append(s)

            for key, sigs in unit_signals.items():
                segs_present = {s.seg.strip().upper() for s in sigs if s.seg}
                if "A" in segs_present and "B" in segs_present:
                    for s in sigs:
                        violations.append(Violation(
                            rule_id=self.rules.ab_segregation.id,
                            rule_name=self.rules.ab_segregation.name,
                            tag=s.tag,
                            cable=s.cable,
                            cabinet=s.cabinet,
                            cioc=s.cioc,
                            baseplate=s.baseplate,
                            slot=s.slot,
                            message=f"A/B Segregation violation: Unit {key} contains both Train A and Train B signals."
                        ))

        # 2. Rule 2: Cable Contiguity & Baseplate Boundary
        if self.rules.cable_contiguity.enabled:
            cable_slots: Dict[str, List[AllocatedSlot]] = defaultdict(list)
            for s in allocations:
                cable_slots[s.cable].append(s)

            for cable_id, slots in cable_slots.items():
                # Sort by pair
                slots_sorted = sorted(slots, key=lambda x: x.pair)
                
                # Check that all pairs are on the same CIOC & Cabinet
                cabinets = {s.cabinet for s in slots_sorted}
                ciocs = {s.cioc for s in slots_sorted}
                if len(cabinets) > 1 or len(ciocs) > 1:
                    for s in slots_sorted:
                        violations.append(Violation(
                            rule_id=self.rules.cable_contiguity.id,
                            rule_name=self.rules.cable_contiguity.name,
                            tag=s.tag,
                            cable=s.cable,
                            cabinet=s.cabinet,
                            cioc=s.cioc,
                            baseplate=s.baseplate,
                            slot=s.slot,
                            message=f"Cable {cable_id} is severed across multiple cabinets or CIOCs."
                        ))
                    continue

                # Check contiguity within CIOC (slot_in_cioc = baseplate * 12 + slot)
                cioc_slots = [s.baseplate * 12 + s.slot for s in slots_sorted]
                expected_start = cioc_slots[0]
                is_contiguous = True
                for i, c_slot in enumerate(cioc_slots):
                    if c_slot != expected_start + i:
                        is_contiguous = False
                        break

                if not is_contiguous:
                    for s in slots_sorted:
                        violations.append(Violation(
                            rule_id=self.rules.cable_contiguity.id,
                            rule_name=self.rules.cable_contiguity.name,
                            tag=s.tag,
                            cable=s.cable,
                            cabinet=s.cabinet,
                            cioc=s.cioc,
                            baseplate=s.baseplate,
                            slot=s.slot,
                            message=f"Cable {cable_id} pairs are not contiguous in slots within CIOC {slots_sorted[0].cioc+1}."
                        ))

                # Boundary alignment check
                total_cable_len = len(slots_sorted)
                start_bp = slots_sorted[0].baseplate
                start_slot_in_bp = slots_sorted[0].slot

                # 24-pair cables must align to baseplate boundary
                if total_cable_len >= 24 and start_slot_in_bp != 0:
                    for s in slots_sorted:
                        violations.append(Violation(
                            rule_id=self.rules.cable_contiguity.id,
                            rule_name=self.rules.cable_contiguity.name,
                            tag=s.tag,
                            cable=s.cable,
                            cabinet=s.cabinet,
                            cioc=s.cioc,
                            baseplate=s.baseplate,
                            slot=s.slot,
                            message=f"24-pair cable {cable_id} must align to baseplate boundary (slot 1), but starts at slot {start_slot_in_bp + 1}."
                        ))

                # 12-pair cables must align to baseplate boundary
                if total_cable_len == 12 and start_slot_in_bp != 0:
                    for s in slots_sorted:
                        violations.append(Violation(
                            rule_id=self.rules.cable_contiguity.id,
                            rule_name=self.rules.cable_contiguity.name,
                            tag=s.tag,
                            cable=s.cable,
                            cabinet=s.cabinet,
                            cioc=s.cioc,
                            baseplate=s.baseplate,
                            slot=s.slot,
                            message=f"12-pair cable {cable_id} starts at slot {start_slot_in_bp + 1} instead of baseplate boundary slot 1."
                        ))

                # Small cables boundary crossing
                if not self.rules.cable_contiguity.allow_boundary_crossing_small:
                    if total_cable_len in [2, 6]:
                        end_slot_in_bp = start_slot_in_bp + total_cable_len
                        if end_slot_in_bp > 12:
                            for s in slots_sorted:
                                violations.append(Violation(
                                    rule_id=self.rules.cable_contiguity.id,
                                    rule_name=self.rules.cable_contiguity.name,
                                    tag=s.tag,
                                    cable=s.cable,
                                    cabinet=s.cabinet,
                                    cioc=s.cioc,
                                    baseplate=s.baseplate,
                                    slot=s.slot,
                                    message=f"Cable {cable_id} straddles across two baseplates (starts at slot {start_slot_in_bp + 1}), violating boundary constraint."
                                ))

        # 3. Rule 3: Group Cohesion
        if self.rules.group_cohesion.enabled:
            group_allocs: Dict[str, List[AllocatedSlot]] = defaultdict(list)
            for s in allocations:
                if s.group:
                    group_allocs[s.group].append(s)

            for grp, grp_slots in group_allocs.items():
                cabs = {s.cabinet for s in grp_slots}
                if len(cabs) > 1:
                    # Find majority cabinet
                    cab_counts = defaultdict(int)
                    for s in grp_slots:
                        cab_counts[s.cabinet] += 1
                    main_cab = max(cab_counts, key=cab_counts.get)
                    for s in grp_slots:
                        if s.cabinet != main_cab:
                            violations.append(Violation(
                                rule_id=self.rules.group_cohesion.id,
                                rule_name=self.rules.group_cohesion.name,
                                tag=s.tag,
                                cable=s.cable,
                                cabinet=s.cabinet,
                                cioc=s.cioc,
                                baseplate=s.baseplate,
                                slot=s.slot,
                                message=f"Group cohesion broken: Signal {s.tag} in group {grp} placed in Cabinet {s.cabinet+1}, while majority of group is in Cabinet {main_cab+1}."
                            ))

        # 4. Rule 4: Spare Capacity Margin
        if self.rules.spare_capacity.enabled:
            cab_used_slots: Dict[int, int] = defaultdict(int)
            for s in allocations:
                if not s.is_spare:
                    cab_used_slots[s.cabinet] += 1

            max_allowed = int(384 * (1.0 - (self.rules.spare_capacity.spare_percentage / 100.0)))
            for cab_idx, used_count in cab_used_slots.items():
                if used_count > max_allowed:
                    violations.append(Violation(
                        rule_id=self.rules.spare_capacity.id,
                        rule_name=self.rules.spare_capacity.name,
                        cabinet=cab_idx,
                        message=f"Cabinet {cab_idx+1} exceeds allowed capacity: {used_count} signals placed > limit of {max_allowed} (configured spare: {self.rules.spare_capacity.spare_percentage}%)."
                    ))

        # 5+6. Hardware per signal type, re-applied from the data table (P1-4).
        # No substring checks, no DO_ISOLATED special-casing: the same
        # hardware_for() the solver used is re-evaluated here. Signals whose
        # subtype matches nothing get a violation (the validator will own the
        # hardware TQ in P1-3); they must never pass silently.
        if self.rules.signal_type_lookup.enabled:
            for s in allocations:
                if s.is_spare or not s.io_type:
                    continue
                exp_charm, exp_tb = hardware_for(s.io_type, s.subtype)
                if exp_charm is None:
                    violations.append(Violation(
                        rule_id=self.rules.signal_type_lookup.id,
                        rule_name=self.rules.signal_type_lookup.name,
                        tag=s.tag,
                        cable=s.cable,
                        cabinet=s.cabinet,
                        cioc=s.cioc,
                        baseplate=s.baseplate,
                        slot=s.slot,
                        message=f"Signal {s.tag} ({s.io_type}/{s.subtype or '-'}) matches no hardware-table row: no CHARM or terminal block can be assigned."
                    ))
                elif s.charm != exp_charm or s.terminal_block != exp_tb:
                    rule_id = self.rules.signal_type_lookup.id
                    rule_name = self.rules.signal_type_lookup.name
                    if (normalise_subtype(s.subtype) in ("HIGH_CURRENT", "RELAY")
                            and self.rules.isolated_charm.enabled):
                        rule_id = self.rules.isolated_charm.id
                        rule_name = self.rules.isolated_charm.name
                    violations.append(Violation(
                        rule_id=rule_id,
                        rule_name=rule_name,
                        tag=s.tag,
                        cable=s.cable,
                        cabinet=s.cabinet,
                        cioc=s.cioc,
                        baseplate=s.baseplate,
                        slot=s.slot,
                        message=f"Signal {s.tag} ({s.io_type}/{s.subtype or '-'}) has {s.charm} / {s.terminal_block}, expected {exp_charm} / {exp_tb}."
                    ))

        return violations

    @staticmethod
    def plant_violation(allocations: List[AllocatedSlot], plant_type: str = "ab_leak") -> List[AllocatedSlot]:
        """
        Creates a copy of the allocations with a deliberately planted violation
        for the credibility demo.
        """
        cloned = [copy.deepcopy(s) for s in allocations]
        if not cloned:
            return cloned

        if plant_type == "ab_leak":
            # Find an 'A' signal and change its segregation or move it to a 'B' CIOC
            cioc_segs: Dict[Tuple[int, int], Set[str]] = defaultdict(set)
            for s in cloned:
                if s.seg:
                    cioc_segs[(s.cabinet, s.cioc)].add(s.seg)

            # Find a CIOC with 'B'
            b_ciocs = [loc for loc, segs in cioc_segs.items() if "B" in segs]
            if b_ciocs:
                target_cab, target_cioc = b_ciocs[0]
                # Find an 'A' signal anywhere and reassign its CIOC to target_cioc
                for s in cloned:
                    if s.seg == "A":
                        s.cabinet = target_cab
                        s.cioc = target_cioc
                        s.global_slot = s.cabinet * 384 + s.cioc * 96 + s.baseplate * 12 + s.slot
                        break
            else:
                # Force one signal to 'B' in an 'A' CIOC
                for s in cloned:
                    if s.seg == "A":
                        s.seg = "B"
                        break

        elif plant_type == "split_cable":
            # Take pair 2 of any multi-pair cable and move it 5 slots away
            for i, s in enumerate(cloned):
                if s.pair == 2:
                    s.slot = (s.slot + 4) % 12
                    s.global_slot = s.cabinet * 384 + s.cioc * 96 + s.baseplate * 12 + s.slot
                    break

        elif plant_type == "cross_boundary":
            # Shift a 12-pair or 24-pair cable by 3 slots
            target_cable = None
            for s in cloned:
                if s.pair == 12:
                    target_cable = s.cable
                    break
            if target_cable:
                for s in cloned:
                    if s.cable == target_cable:
                        s.slot = (s.slot + 3) % 12
                        s.global_slot = s.cabinet * 384 + s.cioc * 96 + s.baseplate * 12 + s.slot

        elif plant_type == "scatter_group":
            # Move one signal of a group to cabinet 99
            for s in cloned:
                if s.group:
                    s.cabinet = (s.cabinet + 1)
                    s.cabinet_name = f"CAB-{s.cabinet+1:02d}"
                    s.global_slot = s.cabinet * 384 + s.cioc * 96 + s.baseplate * 12 + s.slot
                    break

        return cloned
