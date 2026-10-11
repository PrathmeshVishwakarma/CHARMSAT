from typing import Dict, List, Optional, Tuple
from rapidfuzz import fuzz
from pydantic import BaseModel

CANONICAL_FIELDS = [
    "Tag",
    "IO Type",
    "Subtype",
    "Cable",
    "Pair",
    "Cable Size",
    "Group",
    "Segregation"
]

SYNONYM_DICTIONARY = {
    "Tag": [
        "tag", "tag_number", "instrument_tag", "tag_name", "signal_tag", "loop_tag",
        "tagno", "tag id", "tagname", "device_tag", "instrument tag no"
    ],
    "IO Type": [
        "io type", "signal type", "i/o type", "io_type", "type", "channel type",
        "io_category", "signal_category", "i/o", "io_desc", "signal"
    ],
    "Subtype": [
        "subtype", "sub_type", "io_subtype", "device_type", "equip_type",
        "equipment type", "load_type", "isolated_type", "feature"
    ],
    "Cable": [
        "cable", "cable_id", "multicore_ref", "cable_tag", "cable no", "multicore",
        "cable_number", "cable number", "cbl_id", "trunk_cable", "cable ref"
    ],
    "Pair": [
        "pair", "pair_no", "pair_index", "pair number", "core_pair", "pair_num",
        "channel_pair", "pair_id", "pair#"
    ],
    "Cable Size": [
        "cable size", "pairs_total", "cable_pairs", "cable_capacity", "size",
        "total_pairs", "cable cores", "cores", "capacity_pairs", "cable_size"
    ],
    "Group": [
        "group", "unit_area", "process_group", "group_id", "area", "unit",
        "subsystem", "plant_area", "section", "functional_group", "process_area"
    ],
    "Segregation": [
        "segregation", "train", "safety_seg", "seg_a_b", "channel_train",
        "train_id", "train_a_b", "seg", "segregation_class", "division", "train a/b"
    ]
}

class ColumnMatch(BaseModel):
    detected_column: str
    mapped_canonical: Optional[str] = None
    confidence_pct: float = 0.0
    alternative_matches: Dict[str, float] = {}

class ColumnMappingResult(BaseModel):
    matches: List[ColumnMatch]
    unmapped_columns: List[str]
    missing_required: List[str]

class ColumnAutoMapper:
    def __init__(self, threshold: float = 50.0):
        self.threshold = threshold

    def map_columns(self, file_columns: List[str]) -> ColumnMappingResult:
        matches: List[ColumnMatch] = []
        assigned_canonicals = set()

        # Step 1: Compute match scores for each detected column against each canonical field
        candidate_scores: List[Tuple[float, str, str]] = []

        for col in file_columns:
            clean_col = col.strip().lower().replace("-", "_").replace(".", "")
            for canonical, synonyms in SYNONYM_DICTIONARY.items():
                best_score = 0.0
                # Direct match to canonical name
                canonical_score = fuzz.token_sort_ratio(clean_col, canonical.lower().replace("-", "_"))
                best_score = max(best_score, canonical_score)

                # Match against synonyms
                for syn in synonyms:
                    syn_score = fuzz.token_sort_ratio(clean_col, syn.replace("-", "_"))
                    if syn_score > best_score:
                        best_score = syn_score

                candidate_scores.append((best_score, col, canonical))

        # Sort candidate scores descending (greedy assignment)
        candidate_scores.sort(key=lambda x: x[0], reverse=True)

        col_assignments: Dict[str, Tuple[str, float]] = {}
        for score, col, canonical in candidate_scores:
            if col not in col_assignments and canonical not in assigned_canonicals:
                if score >= self.threshold:
                    col_assignments[col] = (canonical, round(score, 1))
                    assigned_canonicals.add(canonical)

        # Build results
        unmapped = []
        for col in file_columns:
            alt_scores = {}
            clean_col = col.strip().lower().replace("-", "_")
            for canonical, synonyms in SYNONYM_DICTIONARY.items():
                s = max([fuzz.token_sort_ratio(clean_col, syn) for syn in synonyms] + [fuzz.token_sort_ratio(clean_col, canonical.lower())])
                alt_scores[canonical] = round(s, 1)

            if col in col_assignments:
                canon, conf = col_assignments[col]
                matches.append(ColumnMatch(
                    detected_column=col,
                    mapped_canonical=canon,
                    confidence_pct=conf,
                    alternative_matches=alt_scores
                ))
            else:
                unmapped.append(col)
                matches.append(ColumnMatch(
                    detected_column=col,
                    mapped_canonical=None,
                    confidence_pct=0.0,
                    alternative_matches=alt_scores
                ))

        # Required fields check
        required_fields = ["Tag", "IO Type", "Cable", "Pair"]
        missing_req = [req for req in required_fields if req not in assigned_canonicals]

        return ColumnMappingResult(
            matches=matches,
            unmapped_columns=unmapped,
            missing_required=missing_req
        )
