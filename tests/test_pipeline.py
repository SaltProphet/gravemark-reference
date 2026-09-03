import copy
import json
from pathlib import Path

from gravemark.evidence import calculate_gravity
from gravemark.normalization import SourceRecord
from gravemark.patterns import PATTERNS
from gravemark.pipeline import run_pipeline


ROOT = Path(__file__).parents[1]


def load_fixture(name):
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


def test_pipeline_is_deterministic_and_golden():
    records = load_fixture("workflow_complaints.json")
    first = run_pipeline(records)
    second = run_pipeline(records)
    assert first == second
    expected = json.loads((ROOT / "fixtures" / "expected" / "workflow_complaints.result.json").read_text(encoding="utf-8"))
    assert first == expected


def test_multiple_patterns_on_one_sentence_have_unique_ids():
    result = run_pipeline([{"source_id": "one", "source_type": "text", "label": "One", "text": "I cannot fix the error and I hate when it crashes.", "provenance": {"fixture": "unit"}}])
    ids = [item["evidence_id"] for item in result["detected_evidence"]]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 3


def test_provenance_survives_to_evidence_and_finding_references():
    result = run_pipeline(load_fixture("operations_complaints.json"))
    by_id = {item["evidence_id"]: item for item in result["detected_evidence"]}
    sources = {item["source_id"]: item for item in result["sources"]}
    assert result["detected_evidence"]
    for evidence in by_id.values():
        assert evidence["provenance"]["fixture"] == "operations_complaints.json"
        assert evidence["source_id"] in sources
    for finding in result["candidate_findings"]:
        assert finding["supporting_evidence_ids"]
        assert set(finding["supporting_evidence_ids"]) <= by_id.keys()


def test_scores_are_recomputable_and_findings_are_ranked():
    result = run_pipeline(load_fixture("reliability_complaints.json"))
    evidence = {item["evidence_id"]: item for item in result["detected_evidence"]}
    for finding in result["candidate_findings"]:
        items = [evidence[item] for item in finding["supporting_evidence_ids"]]
        average = sum(item["deterministic_score"] for item in items) / len(items)
        expected = round(average * (1 + (len(items) - 1) * 0.15), 2)
        assert finding["score"] == expected
    assert [item["rank"] for item in result["candidate_findings"]] == list(range(1, len(result["candidate_findings"]) + 1))


def test_no_match_is_honestly_empty():
    result = run_pipeline([{"source_id": "empty", "source_type": "text", "label": "Empty", "text": "A calm update with no signal words.", "provenance": {}}])
    assert result["detected_evidence"] == []
    assert result["candidate_findings"] == []


def test_near_identical_prefixes_from_unrelated_sources_do_not_collapse():
    text_a = "The process fails because the export is unavailable in the morning."
    text_b = "The process fails because the export is unavailable in the evening."
    result = run_pipeline([
        {"source_id": "a", "source_type": "text", "label": "A", "text": text_a, "provenance": {"record": "a"}},
        {"source_id": "b", "source_type": "text", "label": "B", "text": text_b, "provenance": {"record": "b"}},
    ])
    assert len(result["candidate_findings"]) == 2
    assert all(len(item["supporting_evidence_ids"]) == 1 for item in result["candidate_findings"])


def test_source_record_is_effectively_immutable():
    source = SourceRecord.from_dict({"source_id": "x", "source_type": "text", "label": "X", "text": "cannot proceed", "provenance": {"fixture": "x"}})
    try:
        source.text = "changed"
    except Exception:
        pass
    else:
        raise AssertionError("SourceRecord must be immutable")


def test_spacy_fallback(monkeypatch):
    import gravemark.normalization as normalization

    class FailingSpacy:
        def load(self, _name):
            raise OSError("model unavailable")

        def blank(self, _name):
            import spacy
            return spacy.blank("en")

    monkeypatch.setattr(normalization, "spacy", FailingSpacy())
    nlp = normalization.load_nlp()
    assert "sentencizer" in nlp.pipe_names
    assert normalization.normalize_source(SourceRecord("x", "text", "X", "Cannot proceed."), nlp)
