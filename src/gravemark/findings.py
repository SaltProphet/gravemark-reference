"""Immutable candidate findings with evidence references only."""

from dataclasses import dataclass
from typing import Mapping, Tuple

from .evidence import Evidence
from .scoring import score_finding


@dataclass(frozen=True)
class CandidateFinding:
    finding_id: str
    title_or_label: str
    supporting_evidence_ids: Tuple[str, ...]
    score: float
    score_factors: Mapping[str, float]
    rank: int
    validation_required: bool = True

    def to_dict(self) -> dict:
        return {
            "finding_id": self.finding_id,
            "title_or_label": self.title_or_label,
            "supporting_evidence_ids": list(self.supporting_evidence_ids),
            "score": self.score,
            "score_factors": dict(self.score_factors),
            "rank": self.rank,
            "validation_required": self.validation_required,
        }


def build_findings(groups: tuple[tuple[Evidence, ...], ...]) -> tuple[CandidateFinding, ...]:
    scored = []
    for group in groups:
        result = score_finding(group)
        ids = tuple(item.evidence_id for item in group)
        key = "_".join(ids)
        scored.append((result.score, key, group, result))
    scored.sort(key=lambda item: (-item[0], item[1]))
    findings = []
    for rank, (score, key, group, result) in enumerate(scored, start=1):
        findings.append(CandidateFinding(
            finding_id=f"finding_{rank:03d}_{key}",
            title_or_label=f"{group[0].pattern_id}: {group[0].quote}",
            supporting_evidence_ids=tuple(item.evidence_id for item in group),
            score=score,
            score_factors=result.factors,
            rank=rank,
        ))
    return tuple(findings)
