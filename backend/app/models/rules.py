from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field
import yaml

class RuleABSegregationConfig(BaseModel):
    id: str = "RULE-01"
    name: str = "A/B Segregation"
    enabled: bool = True
    level: Literal["cioc", "cabinet", "baseplate"] = "cioc"
    description: str = "Segregates Train A and Train B field signals into separate hardware units to eliminate common-cause failure."

class RuleCableContiguityConfig(BaseModel):
    id: str = "RULE-02"
    name: str = "Cable Block Contiguity & Boundary"
    enabled: bool = True
    allow_boundary_crossing_small: bool = False  # False means 6-pair/2-pair cannot cross baseplate boundaries
    strict_pair_ordering: bool = True            # Pairs land in ascending slot order
    description: str = "Treats multi-pair cables as atomic blocks; requires 12/24-pair baseplate alignment and controls small cable straddling."

class RuleGroupCohesionConfig(BaseModel):
    id: str = "RULE-03"
    name: str = "Group Cabinet Cohesion & Sequence"
    enabled: bool = True
    target_level: Literal["cabinet", "cioc"] = "cabinet"
    soft_sequence_weight: int = 5                # Objective penalty weight for breaking signal tag sequence
    description: str = "Groups related instruments (e.g. reactor loops) into the same cabinet with sequential slot preference."

class RuleSpareCapacityConfig(BaseModel):
    id: str = "RULE-04"
    name: str = "Cabinet Spare Capacity Margin"
    enabled: bool = True
    spare_percentage: float = 10.0               # Default 10.0% spare room per cabinet
    description: str = "Reserves expansion capacity per cabinet (max used slots <= floor(384 * (1 - spare%)))."

class RuleIsolatedCharmConfig(BaseModel):
    id: str = "RULE-05"
    name: str = "Isolated CHARM Subtypes"
    enabled: bool = True
    isolated_subtypes: List[str] = Field(default_factory=lambda: ["SOV", "horn", "beacon", "ISOLATED"])
    description: str = "Enforces isolated CHARMs with relay terminal blocks for inductive or high-power DO devices."

class CharmHardwareMap(BaseModel):
    charm: str
    terminal_block: str

class RuleSignalTypeLookupConfig(BaseModel):
    id: str = "RULE-06"
    name: str = "Hardware Type Lookup"
    enabled: bool = True
    mapping: Dict[str, CharmHardwareMap] = Field(default_factory=lambda: {
        "AI": CharmHardwareMap(charm="AI 4-20mA HART", terminal_block="Standard TB"),
        "AO": CharmHardwareMap(charm="AO 4-20mA HART", terminal_block="Standard TB"),
        "DI": CharmHardwareMap(charm="DI 24V DC Dry Contact", terminal_block="Standard TB"),
        "DO": CharmHardwareMap(charm="DO 24V DC High-Side", terminal_block="Fused TB"),
        "DO_ISOLATED": CharmHardwareMap(charm="DO 24V DC Isolated", terminal_block="Relay TB"),
        "RTD": CharmHardwareMap(charm="RTD Temperature", terminal_block="RTD TB"),
        "TC": CharmHardwareMap(charm="TC Temperature", terminal_block="Thermocouple TB")
    })
    description: str = "Deterministic lookup mapping electrical signal types to Emerson DeltaV CHARM hardware and terminal blocks."

class RuleNamingPatternsConfig(BaseModel):
    id: str = "RULE-07"
    name: str = "Asset Naming Patterns"
    enabled: bool = True
    cabinet_pattern: str = "CAB-{cab:02d}"
    cioc_pattern: str = "{cab_name}-CIOC-{cioc:02d}"
    cioc_no_format: Literal["hierarchical", "numeric_3digit", "deltav_ar1"] = "deltav_ar1"
    baseplate_pattern: str = "{cioc_no}-CBP-{bp}"
    description: str = "Resolves naming ambiguities (e.g. DeltaV AR1CIOC vs 001-CBP-1) with parameterized template patterns."

class GenericRuleConfig(BaseModel):
    id: str
    name: str
    enabled: bool = True
    relation: Literal["same", "different", "at_most_k"]
    attribute: Literal["group", "seg", "io_type", "subtype"]
    level: Literal["cabinet", "cioc", "baseplate"]
    k_value: int = 1
    description: str = ""

class RuleSetConfig(BaseModel):
    ab_segregation: RuleABSegregationConfig = Field(default_factory=RuleABSegregationConfig)
    cable_contiguity: RuleCableContiguityConfig = Field(default_factory=RuleCableContiguityConfig)
    group_cohesion: RuleGroupCohesionConfig = Field(default_factory=RuleGroupCohesionConfig)
    spare_capacity: RuleSpareCapacityConfig = Field(default_factory=RuleSpareCapacityConfig)
    isolated_charm: RuleIsolatedCharmConfig = Field(default_factory=RuleIsolatedCharmConfig)
    signal_type_lookup: RuleSignalTypeLookupConfig = Field(default_factory=RuleSignalTypeLookupConfig)
    naming_patterns: RuleNamingPatternsConfig = Field(default_factory=RuleNamingPatternsConfig)
    custom_rules: List[GenericRuleConfig] = Field(default_factory=list)

    def to_yaml(self) -> str:
        return yaml.dump(self.model_dump(), sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "RuleSetConfig":
        data = yaml.safe_load(yaml_str)
        return cls.model_validate(data)
