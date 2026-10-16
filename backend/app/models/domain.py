from dataclasses import dataclass, field
from typing import Optional, List, Set, Dict, Any
from pydantic import BaseModel, Field

@dataclass
class Signal:
    tag: str
    io_type: str
    subtype: Optional[str] = None
    cable: str = ""
    pair: int = 1
    group: Optional[str] = None
    seg: Optional[str] = None  # 'A' or 'B' or None
    row_no: int = 0  # original Excel row number (1-based) for TQ provenance
    extra: Dict[str, str] = field(default_factory=dict)  # unmapped columns, usable by rules

@dataclass
class Cable:
    id: str
    size: int  # 2, 6, 12, or 24
    signals: List[Signal] = field(default_factory=list)
    group: Optional[str] = None
    segs: Set[str] = field(default_factory=set)

    @property
    def used_pairs(self) -> int:
        return len(self.signals)

    @property
    def spare_pairs(self) -> int:
        return max(0, self.size - len(self.signals))

class AllocatedSlot(BaseModel):
    tag: Optional[str] = None
    cable: str
    pair: int
    cabinet: int  # 0-indexed
    cioc: int     # 0..3
    baseplate: int # 0..7
    slot: int      # 0..11
    global_slot: int = 0  # cabinet * 384 + cioc * 96 + baseplate * 12 + slot
    cabinet_name: str = ""
    cioc_name: str = ""
    baseplate_name: str = ""
    charm: str = ""
    terminal_block: str = ""
    io_type: Optional[str] = None
    subtype: Optional[str] = None
    group: Optional[str] = None
    seg: Optional[str] = None
    is_spare: bool = False

class Violation(BaseModel):
    rule_id: str
    rule_name: str
    tag: Optional[str] = None
    cable: Optional[str] = None
    cabinet: Optional[int] = None
    cioc: Optional[int] = None
    baseplate: Optional[int] = None
    slot: Optional[int] = None
    message: str

class TQ(BaseModel):
    id: str
    kind: str  # 'data' | 'rule_conflict' | 'capacity'
    items: List[str] = Field(default_factory=list)
    rule_ids: List[str] = Field(default_factory=list)
    message: str

class RevisionMoveDetail(BaseModel):
    tag: str
    cable: str
    io_type: str
    group: Optional[str] = None
    old_location: str
    new_location: str
    forcing_rule: str
    reason: str

class RevisionSummary(BaseModel):
    added_count: int = 0
    deleted_count: int = 0
    changed_count: int = 0
    moved_count: int = 0
    unchanged_count: int = 0
    affected_cabinets: List[int] = Field(default_factory=list)
    moves_ours: int = 0
    moves_from_scratch: int = 0
    moves_detail: List[RevisionMoveDetail] = Field(default_factory=list)

class AllocResult(BaseModel):
    success: bool
    allocations: List[AllocatedSlot] = Field(default_factory=list)
    tqs: List[TQ] = Field(default_factory=list)
    violations: List[Violation] = Field(default_factory=list)
    cabinets_used: int = 0
    slots_used: int = 0
    total_slots_available: int = 0
    coverage_pct: float = 100.0  # (placed + TQ'd) / total
    spare_pct_actual: float = 0.0
    runtime_s: float = 0.0
    lower_bound_cabinets: int = 0
    solver_status: str = "OPTIMAL"
    rev_summary: Optional[RevisionSummary] = None
