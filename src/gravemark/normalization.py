"""Deterministic source normalization and sentence boundaries."""

from dataclasses import dataclass
import hashlib
from typing import Tuple

import spacy

from .patterns import PatternDefinition


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    source_type: str
    label: str
    text: str
    provenance: Tuple[Tuple[str, str], ...] = ()

    @classmethod
    def from_dict(cls, payload: dict) -> "SourceRecord":
        raw_text = str(payload.get("text") or "")
        raw_label = str(payload.get("label") or "text")
        source_id = str(payload.get("source_id") or "").strip()
        if not source_id:
            source_id = "source_" + hashlib.sha256(f"{raw_label}\n{raw_text}".encode("utf-8")).hexdigest()[:12]
        provenance = tuple(sorted((str(k), str(v)) for k, v in (payload.get("provenance") or {}).items()))
        return cls(
            source_id=source_id,
            source_type=str(payload.get("source_type") or "text"),
            label=str(payload.get("label") or source_id),
            text=raw_text,
            provenance=provenance,
        )

    def provenance_dict(self) -> dict:
        return dict(self.provenance)


@dataclass(frozen=True)
class NormalizedSentence:
    source_id: str
    sentence_index: int
    text: str
    start_char: int
    end_char: int


def load_nlp():
    """Preserve legacy model loading and blank-English fallback."""
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        nlp = spacy.blank("en")
        if "parser" not in nlp.pipe_names and "sentencizer" not in nlp.pipe_names:
            nlp.add_pipe("sentencizer")
        return nlp


def normalize_source(source: SourceRecord, nlp=None) -> Tuple[NormalizedSentence, ...]:
    nlp = nlp or load_nlp()
    doc = nlp(source.text)
    return tuple(
        NormalizedSentence(
            source_id=source.source_id,
            sentence_index=index,
            text=sentence.text.strip(),
            start_char=sentence.start_char,
            end_char=sentence.end_char,
        )
        for index, sentence in enumerate(doc.sents)
        if sentence.text.strip()
    )
