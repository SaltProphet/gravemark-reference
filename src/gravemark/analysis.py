"""Validated model-owned analysis contract."""

from dataclasses import dataclass
from typing import Any, Mapping, Tuple


ALLOWED_STATUSES = {"ready", "disabled", "error"}


@dataclass(frozen=True)
class LocalAnalysis:
    status: str
    theme_label: str = ""
    root_cause_hypothesis: str = ""
    candidate_fix_notes: str = ""
    validation_questions: Tuple[str, ...] = ()
    validation_required: bool = True
    based_on_evidence_ids: Tuple[str, ...] = ()
    error: str = ""

    def __post_init__(self):
        if self.status not in ALLOWED_STATUSES:
            raise ValueError(f"unsupported local analysis status: {self.status}")
        if self.status == "ready" and not self.validation_required:
            raise ValueError("model-generated analysis must require validation")

    def to_dict(self) -> dict:
        payload = {
            "status": self.status,
            "theme_label": self.theme_label,
            "root_cause_hypothesis": self.root_cause_hypothesis,
            "candidate_fix_notes": self.candidate_fix_notes,
            "validation_questions": list(self.validation_questions),
            "validation_required": self.validation_required,
            "based_on_evidence_ids": list(self.based_on_evidence_ids),
        }
        if self.error:
            payload["error"] = self.error
        return payload


def parse_local_analysis(payload: Any, allowed_evidence_ids: set[str]) -> LocalAnalysis:
    if not isinstance(payload, Mapping):
        raise ValueError("model output must be a JSON object")
    ids = payload.get("based_on_evidence_ids", [])
    if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
        raise ValueError("based_on_evidence_ids must be a list of strings")
    if not set(ids) <= allowed_evidence_ids:
        raise ValueError("model referenced evidence outside the supplied finding")
    questions = payload.get("validation_questions", [])
    if not isinstance(questions, list) or not all(isinstance(item, str) for item in questions):
        raise ValueError("validation_questions must be a list of strings")
    validation_required = payload.get("validation_required", True)
    if not isinstance(validation_required, bool):
        raise ValueError("validation_required must be boolean")
    return LocalAnalysis(
        status="ready",
        theme_label=str(payload.get("theme_label", "")),
        root_cause_hypothesis=str(payload.get("root_cause_hypothesis", "")),
        candidate_fix_notes=str(payload.get("candidate_fix_notes", "")),
        validation_questions=tuple(questions),
        validation_required=True,
        based_on_evidence_ids=tuple(ids),
    )
