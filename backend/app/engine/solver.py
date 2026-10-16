from typing import List, Dict, Set, Optional, Tuple, Any
from collections import defaultdict
import time
from ortools.sat.python import cp_model
from app.models.domain import Signal, Cable, AllocatedSlot, AllocResult, TQ, RevisionSummary, RevisionMoveDetail
from app.models.rules import RuleSetConfig
from app.engine.naming import NameGenerator
from app.engine.checker import IndependentChecker
from app.engine.hardware import hardware_for

class CharmsatSolver:
    def __init__(self, rules: RuleSetConfig):
        self.rules = rules
        self.name_gen = NameGenerator(rules.naming_patterns)
        self.checker = IndependentChecker(rules)

    def solve(
        self,
        signals: List[Signal],
        cable_sizes: Dict[str, int],
        prev_allocation: Optional[List[AllocatedSlot]] = None,
        time_limit_s: float = 30.0,
        from_scratch_baseline: bool = False
    ) -> AllocResult:
        """
        Main entry point for CP-SAT allocation engine.
        Decomposes into:
        1. Cable Block aggregation
        2. Stage A: Assign cables to Cabinet & CIOC (handles Group cohesion, A/B segregation, Spares, Min-move)
        3. Stage B: Interval packing per CIOC (handles Contiguity, Baseplate boundaries, NoOverlap)
        """
        start_time = time.time()

        # Step 1: Aggregate into Cable Blocks
        cables_dict: Dict[str, Cable] = {}
        for s in signals:
            if s.cable not in cables_dict:
                size = cable_sizes.get(s.cable, 24 if s.pair > 12 else 12 if s.pair > 6 else 6 if s.pair > 2 else 2)
                cables_dict[s.cable] = Cable(id=s.cable, size=size, group=s.group)
            cables_dict[s.cable].signals.append(s)
            if s.seg:
                cables_dict[s.cable].segs.add(s.seg.strip().upper())

        cable_list = list(cables_dict.values())
        if not cable_list:
            return AllocResult(success=True, runtime_s=0.0)

        # Pre-check for conflicting A/B inside single cable (rule 1 + 2 conflict)
        for cbl in cable_list:
            if "A" in cbl.segs and "B" in cbl.segs:
                tq = TQ(
                    id="TQ-RUL-UNSAT-01",
                    kind="rule_conflict",
                    items=[cbl.id],
                    rule_ids=["RULE-01", "RULE-02"],
                    message=f"Cable {cbl.id} carries both Train A and Train B signals: Rule 1 (A/B Segregation) and Rule 2 (Cable Contiguity) are irreconcilably in conflict."
                )
                return AllocResult(
                    success=False,
                    tqs=[tq],
                    solver_status="INFEASIBLE_RULE_CONFLICT",
                    runtime_s=time.time() - start_time
                )

        # Compute lower bound on cabinets
        total_slots_needed = sum(c.size for c in cable_list)
        spare_pct = self.rules.spare_capacity.spare_percentage if self.rules.spare_capacity.enabled else 0.0
        max_slots_per_cab = int(384 * (1.0 - (spare_pct / 100.0)))
        lower_bound_cabs = max(1, (total_slots_needed + max_slots_per_cab - 1) // max_slots_per_cab)

        # Stage A: CP-SAT solve for Cable -> (Cabinet, CIOC)
        stage_a_res, stage_a_tq = self._solve_stage_a(
            cable_list=cable_list,
            lower_bound_cabs=lower_bound_cabs,
            prev_allocation=prev_allocation if not from_scratch_baseline else None,
            time_limit_s=time_limit_s / 2.0
        )

        if not stage_a_res:
            tq_list = [stage_a_tq] if stage_a_tq else []
            return AllocResult(
                success=False,
                tqs=tq_list,
                solver_status="INFEASIBLE_STAGE_A",
                runtime_s=time.time() - start_time,
                lower_bound_cabinets=lower_bound_cabs
            )

        cable_assignments, num_cabs_used, status_a = stage_a_res

        # Stage B: Slot interval packing per CIOC
        stage_b_res, stage_b_tq = self._solve_stage_b(
            cable_list=cable_list,
            cable_assignments=cable_assignments,
            prev_allocation=prev_allocation if not from_scratch_baseline else None,
            time_limit_s=time_limit_s / 2.0
        )

        if not stage_b_res:
            tq_list = [stage_b_tq] if stage_b_tq else []
            return AllocResult(
                success=False,
                tqs=tq_list,
                solver_status="INFEASIBLE_STAGE_B",
                runtime_s=time.time() - start_time,
                lower_bound_cabinets=lower_bound_cabs
            )
        stage_b_starts, status_b = stage_b_res

        # Build final AllocatedSlot records
        allocations = self._build_allocations(cable_list, cable_assignments, stage_b_starts)

        # Independent Checker run
        violations = self.checker.verify(allocations, signals)

        # Calculate revision diff if Rev A exists
        rev_summary = None
        if prev_allocation is not None and not from_scratch_baseline:
            rev_summary = self._compute_revision_diff(
                prev_allocation=prev_allocation,
                new_allocation=allocations,
                signals=signals,
                cable_sizes=cable_sizes
            )

        # Verdict is computed from the real CP-SAT statuses, never hard-coded:
        # OPTIMAL only if every stage proved optimality, else FEASIBLE.
        runtime = time.time() - start_time
        if status_a == cp_model.OPTIMAL and status_b == cp_model.OPTIMAL:
            real_status = "OPTIMAL"
        else:
            real_status = "FEASIBLE"

        return AllocResult(
            success=len(violations) == 0,
            allocations=allocations,
            violations=violations,
            cabinets_used=num_cabs_used,
            slots_used=len([s for s in allocations if not s.is_spare]),
            total_slots_available=num_cabs_used * 384,
            coverage_pct=100.0,
            spare_pct_actual=round(100.0 * (1.0 - len(allocations) / (num_cabs_used * 384)), 1) if num_cabs_used else 0.0,
            runtime_s=round(runtime, 3),
            lower_bound_cabinets=lower_bound_cabs,
            solver_status=real_status,
            rev_summary=rev_summary
        )

    def _solve_stage_a(
        self,
        cable_list: List[Cable],
        lower_bound_cabs: int,
        prev_allocation: Optional[List[AllocatedSlot]] = None,
        time_limit_s: float = 15.0
    ) -> Tuple[Optional[Tuple[Dict[str, Tuple[int, int]], int, int]], Optional[TQ]]:
        """
        Stage A: Assigns each cable c to (cabinet k, cioc j).
        Returns ((assignments, num_cabinets, cp_sat_status), tq).
        """
        max_cabs = max(lower_bound_cabs + 2, int(lower_bound_cabs * 1.3) + 1)
        total_ciocs = max_cabs * 4

        model = cp_model.CpModel()

        # Previous allocation map for min-move
        prev_cable_cioc: Dict[str, int] = {}
        if prev_allocation:
            for s in prev_allocation:
                if s.cable not in prev_cable_cioc:
                    global_cioc = s.cabinet * 4 + s.cioc
                    prev_cable_cioc[s.cable] = global_cioc

        # Decision variable: cable c assigned to global CIOC k
        y = {}
        for c_idx, c in enumerate(cable_list):
            for k in range(total_ciocs):
                y[c_idx, k] = model.NewBoolVar(f"y_{c_idx}_{k}")

        # Each cable assigned to exactly one CIOC
        for c_idx, c in enumerate(cable_list):
            model.Add(sum(y[c_idx, k] for k in range(total_ciocs)) == 1)

        # Capacity per CIOC: sum of sizes <= 96
        for k in range(total_ciocs):
            model.Add(sum(y[c_idx, k] * c.size for c_idx, c in enumerate(cable_list)) <= 96)

        # Capacity per Cabinet with spare margin
        spare_pct = self.rules.spare_capacity.spare_percentage if self.rules.spare_capacity.enabled else 0.0
        max_slots_cab = int(384 * (1.0 - (spare_pct / 100.0)))

        cab_used_vars = []
        for cab in range(max_cabs):
            cab_ciocs = range(cab * 4, (cab + 1) * 4)
            cab_slots = sum(y[c_idx, k] * c.size for c_idx, c in enumerate(cable_list) for k in cab_ciocs)
            model.Add(cab_slots <= max_slots_cab)

            is_cab_used = model.NewBoolVar(f"cab_used_{cab}")
            model.Add(cab_slots > 0).OnlyEnforceIf(is_cab_used)
            model.Add(cab_slots == 0).OnlyEnforceIf(is_cab_used.Not())
            cab_used_vars.append(is_cab_used)

        # Rule 1: A/B Segregation per CIOC
        if self.rules.ab_segregation.enabled:
            for k in range(total_ciocs):
                has_a = model.NewBoolVar(f"has_a_{k}")
                has_b = model.NewBoolVar(f"has_b_{k}")

                for c_idx, c in enumerate(cable_list):
                    if "A" in c.segs:
                        model.Add(y[c_idx, k] <= has_a)
                    if "B" in c.segs:
                        model.Add(y[c_idx, k] <= has_b)

                model.Add(has_a + has_b <= 1)

        # Rule 3: Group Cohesion (all cables in same group must be in same cabinet)
        if self.rules.group_cohesion.enabled:
            groups_dict: Dict[str, List[int]] = defaultdict(list)
            for c_idx, c in enumerate(cable_list):
                if c.group:
                    groups_dict[c.group].append(c_idx)

            for grp, c_indices in groups_dict.items():
                if len(c_indices) > 1:
                    grp_cab_vars = [model.NewBoolVar(f"grp_{grp}_cab_{cab}") for cab in range(max_cabs)]
                    model.Add(sum(grp_cab_vars) == 1)

                    for c_idx in c_indices:
                        for cab in range(max_cabs):
                            cab_ciocs = range(cab * 4, (cab + 1) * 4)
                            cab_assigned = sum(y[c_idx, k] for k in cab_ciocs)
                            model.Add(cab_assigned == 1).OnlyEnforceIf(grp_cab_vars[cab])

        # Objective formulation:
        obj_terms = []

        # Move penalty
        move_vars = []
        if prev_cable_cioc:
            for c_idx, c in enumerate(cable_list):
                if c.id in prev_cable_cioc:
                    old_k = prev_cable_cioc[c.id]
                    if old_k < total_ciocs:
                        model.AddHint(y[c_idx, old_k], 1)
                        moved = model.NewBoolVar(f"moved_{c_idx}")
                        model.Add(y[c_idx, old_k] == 0).OnlyEnforceIf(moved)
                        model.Add(y[c_idx, old_k] == 1).OnlyEnforceIf(moved.Not())
                        move_vars.append(moved)

            if move_vars:
                obj_terms.append(sum(move_vars) * 10000)

        # Cabinets penalty
        obj_terms.append(sum(cab_used_vars) * 100)

        model.Minimize(sum(obj_terms))

        # Solve: single worker + deterministic time limit + fixed seed, so the
        # same input gives the same output in every process (P1-5). Never use
        # interleave_search: experimental, crashed CP-SAT 9.15 (see blueprint).
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_s
        solver.parameters.num_workers = 1
        solver.parameters.max_deterministic_time = time_limit_s
        solver.parameters.random_seed = 7
        status = solver.Solve(model)

        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            tq = TQ(
                id="TQ-RUL-STAGE-A",
                kind="rule_conflict",
                items=[c.id for c in cable_list[:5]],
                rule_ids=["RULE-01", "RULE-03", "RULE-04"],
                message="CP-SAT could not satisfy A/B Segregation, Group Cohesion, and Spare Capacity simultaneously with available cabinets."
            )
            return None, tq

        assignments: Dict[str, Tuple[int, int]] = {}
        cabs_used = set()
        for c_idx, c in enumerate(cable_list):
            for k in range(total_ciocs):
                if solver.Value(y[c_idx, k]) == 1:
                    cab = k // 4
                    cioc = k % 4
                    assignments[c.id] = (cab, cioc)
                    cabs_used.add(cab)
                    break

        return (assignments, len(cabs_used), status), None

    def _solve_stage_b(
        self,
        cable_list: List[Cable],
        cable_assignments: Dict[str, Tuple[int, int]],
        prev_allocation: Optional[List[AllocatedSlot]] = None,
        time_limit_s: float = 15.0
    ) -> Tuple[Optional[Tuple[Dict[str, int], int]], Optional[TQ]]:
        """
        Stage B: 1-D Interval Packing per CIOC (96 slots).
        Returns ((cable_id -> start_slot_in_cioc (0..95), worst cp_sat_status), tq).
        """
        cioc_cables: Dict[Tuple[int, int], List[Cable]] = defaultdict(list)
        for c in cable_list:
            loc = cable_assignments[c.id]
            cioc_cables[loc].append(c)

        prev_start_slots: Dict[str, int] = {}
        if prev_allocation:
            for s in prev_allocation:
                if s.pair == 1:
                    slot_in_cioc = s.baseplate * 12 + s.slot
                    prev_start_slots[s.cable] = slot_in_cioc

        final_starts: Dict[str, int] = {}
        worst_status = cp_model.OPTIMAL

        for (cab, cioc), c_sublist in cioc_cables.items():
            model = cp_model.CpModel()
            starts = {}
            intervals = []

            for c in c_sublist:
                s_var = model.NewIntVar(0, 96 - c.size, f"start_{c.id}")
                e_var = model.NewIntVar(c.size, 96, f"end_{c.id}")
                interval = model.NewIntervalVar(s_var, c.size, e_var, f"interval_{c.id}")
                starts[c.id] = s_var
                intervals.append(interval)

                # Boundary Alignment constraints
                if c.size >= 24:
                    bp_idx = model.NewIntVar(0, 6, f"bp_{c.id}")
                    model.Add(s_var == bp_idx * 12)
                elif c.size == 12:
                    bp_idx = model.NewIntVar(0, 7, f"bp_{c.id}")
                    model.Add(s_var == bp_idx * 12)
                elif not self.rules.cable_contiguity.allow_boundary_crossing_small:
                    bp_idx = model.NewIntVar(0, 7, f"bp_small_{c.id}")
                    offset = model.NewIntVar(0, 12 - c.size, f"off_{c.id}")
                    model.Add(s_var == bp_idx * 12 + offset)

                # Hint from prev_allocation
                if c.id in prev_start_slots:
                    model.AddHint(s_var, prev_start_slots[c.id])

            model.AddNoOverlap(intervals)

            obj_terms = []
            for c in c_sublist:
                if c.id in prev_start_slots:
                    diff = model.NewIntVar(0, 96, f"diff_{c.id}")
                    model.AddAbsEquality(diff, starts[c.id] - prev_start_slots[c.id])
                    obj_terms.append(diff * 10)

            if obj_terms:
                model.Minimize(sum(obj_terms))

            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = max(1.0, time_limit_s / max(1, len(cioc_cables)))
            solver.parameters.num_workers = 1
            solver.parameters.max_deterministic_time = max(1.0, time_limit_s / max(1, len(cioc_cables)))
            solver.parameters.random_seed = 7
            status = solver.Solve(model)

            if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                tq = TQ(
                    id="TQ-RUL-STAGE-B",
                    kind="rule_conflict",
                    items=[c.id for c in c_sublist],
                    rule_ids=["RULE-02"],
                    message=f"Cable interval packing failed on Cabinet {cab+1} CIOC {cioc+1}: boundary alignment constraints could not be packed into 96 slots without overlap."
                )
                return None, tq

            for c in c_sublist:
                final_starts[c.id] = solver.Value(starts[c.id])
            if status == cp_model.FEASIBLE:
                worst_status = cp_model.FEASIBLE

        return (final_starts, worst_status), None

    def _build_allocations(
        self,
        cable_list: List[Cable],
        cable_assignments: Dict[str, Tuple[int, int]],
        start_slots: Dict[str, int]
    ) -> List[AllocatedSlot]:
        allocations: List[AllocatedSlot] = []

        for c in cable_list:
            cab, cioc = cable_assignments[c.id]
            start_in_cioc = start_slots[c.id]
            sig_map = {s.pair: s for s in c.signals}

            for p in range(1, c.size + 1):
                slot_in_cioc = start_in_cioc + (p - 1)
                bp = slot_in_cioc // 12
                sl = slot_in_cioc % 12
                cab_name, cioc_name, bp_name = self.name_gen.get_names(cab, cioc, bp)

                s = sig_map.get(p)
                if s:
                    # Hardware comes from the data table (P1-4). No match ->
                    # TBD placeholder; the validator raises the hardware TQ.
                    charm_name, tb_name = hardware_for(s.io_type, s.subtype)
                    if charm_name is None:
                        charm_name, tb_name = "TBD - see TQ", "TBD - see TQ"

                    alloc = AllocatedSlot(
                        tag=s.tag,
                        cable=s.cable,
                        pair=p,
                        cabinet=cab,
                        cioc=cioc,
                        baseplate=bp,
                        slot=sl,
                        global_slot=cab * 384 + cioc * 96 + bp * 12 + sl,
                        cabinet_name=cab_name,
                        cioc_name=cioc_name,
                        baseplate_name=bp_name,
                        charm=charm_name,
                        terminal_block=tb_name,
                        io_type=s.io_type,
                        subtype=s.subtype,
                        group=s.group,
                        seg=s.seg,
                        is_spare=False
                    )
                else:
                    # Spare pair within multi-pair cable
                    alloc = AllocatedSlot(
                        tag=None,
                        cable=c.id,
                        pair=p,
                        cabinet=cab,
                        cioc=cioc,
                        baseplate=bp,
                        slot=sl,
                        global_slot=cab * 384 + cioc * 96 + bp * 12 + sl,
                        cabinet_name=cab_name,
                        cioc_name=cioc_name,
                        baseplate_name=bp_name,
                        charm="SPARE CHARM",
                        terminal_block="SPARE TB",
                        is_spare=True
                    )
                allocations.append(alloc)

        # Sort allocations cleanly by global slot
        allocations.sort(key=lambda a: a.global_slot)
        return allocations

    def _compute_revision_diff(
        self,
        prev_allocation: List[AllocatedSlot],
        new_allocation: List[AllocatedSlot],
        signals: List[Signal],
        cable_sizes: Dict[str, int]
    ) -> RevisionSummary:
        """
        Computes the diff summary between Rev A and Rev B.
        Also runs a from-scratch baseline re-solve to contrast with our min-move solver!
        """
        prev_by_tag: Dict[str, AllocatedSlot] = {s.tag: s for s in prev_allocation if s.tag}
        new_by_tag: Dict[str, AllocatedSlot] = {s.tag: s for s in new_allocation if s.tag}

        prev_tags = set(prev_by_tag.keys())
        new_tags = set(new_by_tag.keys())

        added_tags = new_tags - prev_tags
        deleted_tags = prev_tags - new_tags
        common_tags = prev_tags & new_tags

        changed_count = 0
        moves_detail: List[RevisionMoveDetail] = []
        affected_cabinets = set()

        for tag in common_tags:
            p_slot = prev_by_tag[tag]
            n_slot = new_by_tag[tag]

            # IO type changed?
            if p_slot.io_type != n_slot.io_type:
                changed_count += 1

            # Moved slot?
            if (p_slot.cabinet != n_slot.cabinet or
                p_slot.cioc != n_slot.cioc or
                p_slot.baseplate != n_slot.baseplate or
                p_slot.slot != n_slot.slot):
                
                affected_cabinets.add(p_slot.cabinet)
                affected_cabinets.add(n_slot.cabinet)

                # Determine forcing rule
                forcing_rule = "RULE-02 (Cable Alignment)"
                reason = "Adjacent cable expansion shifted baseplate boundary"
                if p_slot.cabinet != n_slot.cabinet:
                    forcing_rule = "RULE-03 (Group Cohesion)"
                    reason = "Group membership or cabinet capacity threshold triggered migration"

                moves_detail.append(RevisionMoveDetail(
                    tag=tag,
                    cable=n_slot.cable,
                    io_type=n_slot.io_type or "AI",
                    group=n_slot.group,
                    old_location=f"CAB-{p_slot.cabinet+1:02d} / CIOC-{p_slot.cioc+1} / BP-{p_slot.baseplate+1} / S-{p_slot.slot+1}",
                    new_location=f"CAB-{n_slot.cabinet+1:02d} / CIOC-{n_slot.cioc+1} / BP-{n_slot.baseplate+1} / S-{n_slot.slot+1}",
                    forcing_rule=forcing_rule,
                    reason=reason
                ))

        # Solve from-scratch without hints to measure baseline churn
        scratch_res = self.solve(
            signals=signals,
            cable_sizes=cable_sizes,
            prev_allocation=None,
            time_limit_s=10.0,
            from_scratch_baseline=True
        )

        scratch_by_tag = {s.tag: s for s in scratch_res.allocations if s.tag}
        moves_scratch_count = 0
        for tag in common_tags:
            if tag in scratch_by_tag:
                p_slot = prev_by_tag[tag]
                s_slot = scratch_by_tag[tag]
                if (p_slot.cabinet != s_slot.cabinet or
                    p_slot.cioc != s_slot.cioc or
                    p_slot.baseplate != s_slot.baseplate or
                    p_slot.slot != s_slot.slot):
                    moves_scratch_count += 1

        return RevisionSummary(
            added_count=len(added_tags),
            deleted_count=len(deleted_tags),
            changed_count=changed_count,
            moved_count=len(moves_detail),
            unchanged_count=len(common_tags) - len(moves_detail),
            affected_cabinets=sorted(list(affected_cabinets)),
            moves_ours=len(moves_detail),
            moves_from_scratch=moves_scratch_count,
            moves_detail=moves_detail
        )
