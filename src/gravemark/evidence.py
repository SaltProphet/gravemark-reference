"""Immutable deterministic Evidence objects."""

from dataclasses import dataclass
from typing import Tuple

from .normalization import NormalizedSentence, SourceRecord
from .patterns import MONETIZATION_MULTIPLIERS, PatternDefinition


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    source_id: str
    pattern_id: str
    quote: str
    matched_terms: Tuple[str, ...]
    sentence_index: int
    start_char: int
    end_char: int
    deterministic_score: float
    provenance: Tuple[Tuple[str, str], ...]

    def to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "source_id": self.source_id,
            "pattern_id": self.pattern_id,
            "quote": self.quote,
            "matched_terms": list(self.matched_terms),
            "sentence_index": self.sentence_index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "deterministic_score": self.deterministic_score,
            "provenance": dict(self.provenance),
        }


def calculate_gravity(text: str, pattern: PatternDefinition) -> float:
    """Legacy PainReaperLocal gravity formula."""
    base = pattern.weight
    if any(term in text.lower() for term in ["api", "excel", "salesforce", "quickbooks", "slack"]):
        base += 0.5
    depth = min(1.0, len(text.split()) / 30)
    base += depth * 0.3
    return round(base * MONETIZATION_MULTIPLIERS.get(pattern.pattern_id, 1.0), 2)


def detect_evidence(source: SourceRecord, sentences: tuple[NormalizedSentence, ...], patterns: tuple[PatternDefinition, ...]) -> tuple[Evidence, ...]:
    evidence = []
    for sentence in sentences:
        lowered = sentence.text.lower()
        for pattern in patterns:
            matched_terms = tuple(term for term in pattern.terms if term.lower() in lowered)
            if not matched_terms:
                continue
            evidence_id = f"ev_{source.source_id}_{sentence.sentence_index:03d}_{pattern.pattern_id}"
            evidence.append(Evidence(
                evidence_id=evidence_id,
                source_id=source.source_id,
                pattern_id=pattern.pattern_id,
                quote=sentence.text,
                matched_terms=matched_terms,
                sentence_index=sentence.sentence_index,
                start_char=sentence.start_char,
                end_char=sentence.end_char,
                deterministic_score=calculate_gravity(sentence.text, pattern),
                provenance=source.provenance,
            ))
    return tuple(evidence)
