# Extraction Notes

## Behavioral source

The deterministic behavior was extracted from `C:\Gravemark\gravemark-clean\pain-signal-harvester\src\reaper_engine.py`, specifically:

- `load_nlp()` and its `en_core_web_sm` → blank English + sentencizer fallback;
- `PainReaperLocal.patterns`, preserving all 11 pattern IDs, terms, and weights;
- `PainReaperLocal._calculate_gravity()`, preserving domain-term bonus, text-depth bonus, multipliers, and rounding;
- `PainReaperLocal.detect()`, preserving sentence iteration, case-insensitive substring matching, and matched-term ordering.

## Deliberate correctness changes

Evidence IDs now include source, sentence index, and pattern ID. This fixes the legacy collision where multiple patterns matching one sentence shared `signal_<source>_<sentence>`.

The legacy first-60-character grouping was replaced with exact normalized quote + pattern grouping. This is conservative, deterministic, and prevents unrelated records with the same prefix from collapsing. The difference is required by the Phase 1 referential-integrity and grouping requirements.

Runtime timestamps and UUID run IDs were removed from canonical output. They do not affect detection or scores and would violate deterministic golden comparisons.

## Reused concepts

The source-record boundary follows the newer `src/gravemark/models/evidence.py` and source-pack concepts, while the explicit pattern/scoring separation follows `src/gravemark`.

## Excluded internal components

The public reference intentionally excludes the React and Streamlit UIs, FastAPI, SQLite history and diagnostics, URL fetching, Scout, Docker, MCP, local AI, the marketplace detector, deployment configuration, and operational telemetry.
