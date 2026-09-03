"""Canonical deterministic Phase 1 pipeline."""

from typing import Iterable, Mapping

from .evidence import detect_evidence
from .findings import build_findings
from .grouping import group_evidence
from .normalization import SourceRecord, normalize_source
from .patterns import PATTERNS


def run_pipeline(source_records: Iterable[SourceRecord | Mapping]) -> dict:
    sources = tuple(
        item if isinstance(item, SourceRecord) else SourceRecord.from_dict(item)
        for item in source_records
    )
    normalized = tuple(sentence for source in sources for sentence in normalize_source(source))
    evidence = tuple(
        item
        for source in sources
        for item in detect_evidence(source, normalize_source(source), PATTERNS)
    )
    groups = group_evidence(evidence)
    findings = build_findings(groups)
    evidence_by_id = {item.evidence_id: item for item in evidence}
    for finding in findings:
        if not finding.supporting_evidence_ids or not set(finding.supporting_evidence_ids) <= evidence_by_id.keys():
            raise AssertionError("candidate finding has an unresolved evidence reference")
    return {
        "sources": [
            {
                "source_id": source.source_id,
                "source_type": source.source_type,
                "label": source.label,
                "text": source.text,
                "provenance": source.provenance_dict(),
            }
            for source in sources
        ],
        "normalized_sentences": [
            {
                "source_id": item.source_id,
                "sentence_index": item.sentence_index,
                "text": item.text,
                "start_char": item.start_char,
                "end_char": item.end_char,
            }
            for item in normalized
        ],
        "detected_evidence": [item.to_dict() for item in evidence],
        "candidate_findings": [item.to_dict() for item in findings],
        "deterministic_metadata": {
            "pipeline_version": "gravemark-reference-0.1",
            "pattern_registry": [item.pattern_id for item in PATTERNS],
            "scoring_rule": "legacy_gravity_average_plus_frequency_bonus",
        },
    }
