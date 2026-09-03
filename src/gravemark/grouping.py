"""Conservative, explainable deterministic grouping."""

import re
from collections import defaultdict
from typing import Sequence

from .evidence import Evidence


def _group_key(item: Evidence) -> tuple[str, str]:
    # Exact normalized quote + pattern permits repeated evidence aggregation,
    # while preventing unrelated records with a shared prefix from collapsing.
    normalized_quote = re.sub(r"\s+", " ", item.quote.strip().lower())
    return item.pattern_id, normalized_quote


def group_evidence(evidence: Sequence[Evidence]) -> tuple[tuple[Evidence, ...], ...]:
    groups = defaultdict(list)
    for item in evidence:
        groups[_group_key(item)].append(item)
    return tuple(tuple(groups[key]) for key in sorted(groups))
