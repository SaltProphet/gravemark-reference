"""Deterministic evidence and finding scoring."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

from .evidence import Evidence


@dataclass(frozen=True)
class FindingScore:
    score: int
    factors: Mapping[str, float]


def score_finding(evidence: Sequence[Evidence]) -> FindingScore:
    if not evidence:
        raise ValueError("a finding requires evidence")
    average = sum(item.deterministic_score for item in evidence) / len(evidence)
    frequency_bonus = (len(evidence) - 1) * 0.15
    score = round(average * (1 + frequency_bonus), 2)
    factors = {
        "average_evidence_score": round(average, 2),
        "evidence_count": len(evidence),
        "frequency_bonus": round(frequency_bonus, 2),
    }
    return FindingScore(score=score, factors=MappingProxyType(factors))
