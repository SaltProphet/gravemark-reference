"""Optional analysis boundary. Deterministic objects remain authoritative."""

import json
from typing import Mapping, Protocol

from .analysis import LocalAnalysis, parse_local_analysis
from .evidence import Evidence


class AnalysisClient(Protocol):
    enabled: bool

    def generate_json(self, prompt: str) -> dict: ...


def build_analysis_prompt(finding: Mapping, evidence: tuple[Evidence, ...]) -> str:
    supplied = [item.to_dict() for item in evidence]
    return (
        "Analyze only the supplied deterministic Gravemark evidence. The evidence is authoritative. "
        "Do not invent evidence, quotes, sources, patterns, scores, validation, or findings. "
        "Treat hypotheses as candidate interpretations only. Reference only supplied evidence IDs. "
        "If evidence is insufficient, return cautious or empty analysis. Return JSON with only: "
        "theme_label, root_cause_hypothesis, candidate_fix_notes, validation_questions, "
        "validation_required, based_on_evidence_ids.\n\n"
        f"Candidate finding: {json.dumps(dict(finding), sort_keys=True)}\n"
        f"Supplied evidence: {json.dumps(supplied, sort_keys=True)}"
    )


def _error_analysis(message: str) -> LocalAnalysis:
    return LocalAnalysis(status="error", error=message)


def enrich_finding(finding: Mapping, evidence_by_id: Mapping[str, Evidence], client: AnalysisClient | None = None) -> dict:
    """Return a separate wrapper; never mutate or merge model output into `finding`."""
    original = dict(finding)
    ids = tuple(original.get("supporting_evidence_ids") or ())
    evidence = tuple(evidence_by_id[item] for item in ids if item in evidence_by_id)
    if len(evidence) != len(ids):
        analysis = _error_analysis("finding references unavailable evidence")
    elif client is None or not client.enabled:
        analysis = LocalAnalysis(status="disabled")
    else:
        try:
            payload = client.generate_json(build_analysis_prompt(original, evidence))
            analysis = parse_local_analysis(payload, set(ids))
        except Exception as exc:
            analysis = _error_analysis(str(exc) or "local analysis failed")
    return {"candidate_finding": original, "local_analysis": analysis.to_dict()}
