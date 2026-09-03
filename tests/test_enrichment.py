from copy import deepcopy

from gravemark.enrichment import enrich_finding
from gravemark.evidence import Evidence


FINDING = {
    "finding_id": "finding_001",
    "title_or_label": "VERB_FAIL",
    "supporting_evidence_ids": ["ev_a_000_VERB_FAIL"],
    "score": 7.2,
    "rank": 1,
    "validation_required": True,
}
EVIDENCE = Evidence(
    evidence_id="ev_a_000_VERB_FAIL",
    source_id="a",
    pattern_id="VERB_FAIL",
    quote="The export crashes.",
    matched_terms=("crash",),
    sentence_index=0,
    start_char=0,
    end_char=20,
    deterministic_score=3.8,
    provenance=(("fixture", "unit"),),
)


class FakeClient:
    enabled = True

    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.prompt = ""

    def generate_json(self, prompt):
        self.prompt = prompt
        if self.error:
            raise self.error
        return self.payload


def snapshot(value):
    return deepcopy(value)


def test_valid_enrichment_is_separate_and_uses_supplied_id():
    client = FakeClient({
        "theme_label": "Export reliability",
        "root_cause_hypothesis": "The export path may lack robust error handling.",
        "candidate_fix_notes": "Inspect retry and error feedback.",
        "validation_questions": ["Does this reproduce across file types?"],
        "validation_required": True,
        "based_on_evidence_ids": [EVIDENCE.evidence_id],
        "quote": "hostile fields are ignored",
        "score": 999,
    })
    before = snapshot(FINDING)
    result = enrich_finding(FINDING, {EVIDENCE.evidence_id: EVIDENCE}, client)
    assert result["candidate_finding"] == before
    assert result["local_analysis"]["status"] == "ready"
    assert result["local_analysis"]["based_on_evidence_ids"] == [EVIDENCE.evidence_id]
    assert "score" not in result["local_analysis"]
    assert EVIDENCE.quote in client.prompt


def test_disabled_model_preserves_deterministic_result():
    before = snapshot(FINDING)
    result = enrich_finding(FINDING, {EVIDENCE.evidence_id: EVIDENCE})
    assert result["candidate_finding"] == before
    assert result["local_analysis"]["status"] == "disabled"


def test_unavailable_timeout_and_malformed_output_preserve_result():
    before = snapshot(FINDING)
    for client in [
        FakeClient(error=TimeoutError("timeout")),
        FakeClient(error=ConnectionError("offline")),
        FakeClient(payload="not an object"),
    ]:
        result = enrich_finding(FINDING, {EVIDENCE.evidence_id: EVIDENCE}, client)
        assert result["candidate_finding"] == before
        assert result["local_analysis"]["status"] == "error"


def test_evidence_injection_attempt_is_rejected_without_authority_change():
    before = snapshot(FINDING)
    result = enrich_finding(FINDING, {EVIDENCE.evidence_id: EVIDENCE}, FakeClient({
        "theme_label": "Injected",
        "evidence": [{"evidence_id": "fake", "quote": "fabricated", "pattern": "FAKE", "source": "fake"}],
        "evidence_id": "fake",
        "quote": "fabricated",
        "pattern": "FAKE",
        "source": "fake",
        "score": 0,
        "rank": 999,
        "supporting_evidence_ids": [],
        "based_on_evidence_ids": ["fake"],
    }))
    assert result["candidate_finding"] == before
    assert result["local_analysis"]["status"] == "error"


def test_finding_membership_and_provenance_cannot_change():
    before = snapshot(FINDING)
    result = enrich_finding(FINDING, {EVIDENCE.evidence_id: EVIDENCE}, FakeClient({
        "theme_label": "Attempt",
        "based_on_evidence_ids": [EVIDENCE.evidence_id, "new_id"],
        "source_id": "other",
        "provenance": {"fixture": "other"},
        "validation_required": False,
    }))
    assert result["candidate_finding"] == before
    assert result["local_analysis"]["status"] == "error"
