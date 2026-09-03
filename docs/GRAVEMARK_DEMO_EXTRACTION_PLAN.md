# Gravemark Public Demo Extraction Plan

## 1. Executive Summary

This audit inspected the Gravemark checkout at `C:\Gravemark\gravemark-clean`. The requested workspace, `C:\Users\Shadow\Documents\ChatGPT\Gravemark Demo V1`, is an empty Git repository with no commits, so it is not the source checkout.

Gravemark currently contains two partially overlapping processing paths:

1. The legacy `PainReaperLocal` path in `pain-signal-harvester/src/reaper_engine.py`. It uses spaCy sentence segmentation, an 11-pattern keyword registry, gravity scoring, and quote-prefix clustering.
2. The newer `src/gravemark` path. Its `run_market_scan()` flow uses source packs, a target-profile-driven `MarketplacePatternsDetector`, configurable scoring profiles, a market-scan output pack, and a run manifest.

The newer path is the better extraction seam for a public reference implementation, but it does not currently implement the requested REAPER/spaCy evidence flow. It is a marketplace-offer detector, not a general pain-signal detector; it performs line splitting rather than spaCy normalization; and it emits dictionaries rather than the legacy Evidence-shaped signals. The legacy path has the requested deterministic core but weakly structured provenance and no formal normalization stage.

Recommended strategy: create a reduced, sanitized reference implementation that preserves the legacy deterministic detector behavior where required, copies only the minimal source/schema/scoring/analysis pieces, and exposes a small local API or CLI. Do not extract the full FastAPI/dashboard/SQLite/scraping surface. Keep the AI adapter optional and append-only under `local_analysis`.

Overall classification of the 32 meaningful components inventoried below: **KEEP 11, ADAPT 14, PRIVATE 5, DEAD / STALE 2**.

Major blockers are the path mismatch, two incompatible data contracts, non-deterministic timestamps/run IDs in otherwise repeatable outputs, incomplete provenance propagation in the new path, and the absence of an existing end-to-end test for the exact evidence/analysis boundary.

## 2. Current Architecture

### Deterministic legacy path

`api.py` creates a module-level `reaper = PainReaperLocal()`. `PainReaperLocal.__init__()` calls `load_nlp()`, which first tries `spacy.load("en_core_web_sm")` and falls back to `spacy.blank("en")` plus a sentencizer. `detect()` walks `doc.sents`, checks each sentence against the in-class `self.patterns` registry, calculates a gravity score, and returns dictionaries containing `signal_id`, source fields, quote, pattern, matched terms, score, and `created_at`. `cluster_and_score()` groups by a normalized first-60-character quote prefix and returns ranked dictionaries containing the original group as `evidence_objects`.

The legacy path is served by `/detect`, `/detect-file`, `/detect-pdf`, and `/detect-url`. It is also used by the legacy Streamlit UI.

### Gravemark package path

`src/gravemark/runs/runner.py:run_market_scan()` resolves a source pack, target profile, scoring profile, and output pack. `PasteTextSource` wraps the entire input in one `EvidenceInput`; `CsvFileSource` creates one input per CSV row; local-file and PDF packs create one input per file. `MarketplacePatternsDetector.detect()` splits text into non-empty lines and extracts prices, delivery times, tool terms, target terms, risk terms, and buyer-problem terms. `run_market_scan()` scores each raw detector row and returns `findings`, `clusters` (the same list, with no real aggregation), `market_scan_table`, and a manifest.

This path is served by `/gravemark/runs/market-scan`. It is data-driven for targets and scoring profiles, but its detector is not spaCy-based and its `EvidenceInput` is only an ingestion wrapper; the detector output is not converted into the `EvidenceInput` model.

### Analysis path

`/enrich` calls `src/ai_enrichment.py:enrich_clusters()`. It filters clusters without a quote or `evidence_objects`, then `enrich_cluster()` sends already-detected cluster data to `LocalAIClient` through strict prompts. It returns the original cluster plus `detected_evidence` and `local_analysis`. AI errors return the original cluster with a status of `error`; disabled AI returns status `disabled`.

The market-scan endpoint does not call `/enrich` internally. The frontend makes a separate enrichment request after a deterministic run. This is a useful boundary for the demo, but it must be made explicit in the public API contract.

## 3. End-to-End Execution Trace

Representative input from `tests/test_gravemark_modules.py`:

> `I will setup n8n automation for leads and CRM follow-up. Starting at $99 with delivery in 3 days using n8n, Google Sheets, and HubSpot.`

The actual current Gravemark package path is:

1. `run_market_scan(text, target_id="n8n_workflows", scoring_profile_id="fast_to_market", output_pack_id="market_scan_table")` creates a UUID-derived `run_id`.
2. `get_source_pack("paste_text")` returns `PasteTextSource`; `collect()` calls `make_evidence_input()` and creates one `EvidenceInput` with `source_id="manual_paste"`, `source_type="paste_text"`, the full text in `content`, and metadata containing `origin`, `created_at`, null `source_url`, and null `filename`.
3. `normalize_target_profile_id()` leaves `n8n_workflows` unchanged. `load_target_profile()` reads `src/gravemark/targets/n8n_workflows.v1.json` and adds `_profile_meta`.
4. `get_scoring_profile("fast_to_market")` constructs `FastToMarketScoring` and adds `profile_meta`.
5. `MarketplacePatternsDetector.detect()` splits the input into one line. It detects `prices=["$99"]`, `delivery_times=["3 days"]`, tool terms including `n8n`, `google sheets`, and `hubspot`, and target hits from the profile. It returns one raw finding with `source_location="line:1"` and the full line as `evidence_quote`.
6. `FastToMarketScoring.score(raw)` computes deterministic factors and returns a `ScoreResult(gravity_score, verdict, factors)`. `run_market_scan()` copies the quote, source ID, tags, risk flags, extracted fields, and score into a finding dictionary. It sets `frequency=1` and `final_priority=score.gravity_score`.
7. `render_market_scan(findings)` produces one presentation row. There is no grouping or aggregation on this path: `clusters` is an alias of `findings`.
8. `build_run_manifest()` and `enrich_manifest_diagnostics()` add run, profile, result, diagnostic, and reproducibility metadata.
9. The API endpoint `/gravemark/runs/market-scan` persists latest state and run history in `gravemark_runs.db`, then returns the result. The frontend's `callGravemarkMarketScan()` consumes it.
10. Optional analysis is a separate request: the frontend calls `/enrich` with the returned clusters. `enrich_cluster()` derives a separate `detected_evidence` summary from existing evidence objects and stores model output only in `local_analysis`.

The exact legacy REAPER path differs: `/detect` calls `PainReaperLocal.detect()`, which uses spaCy sentence segmentation and the in-class `patterns` registry; then `cluster_and_score()` creates `evidence_objects`; then the frontend or `/enrich` can add AI analysis. It is the path that most closely matches the requested raw text → spaCy → deterministic Evidence flow.

## 4. Component Inventory

| Component | Location | Actual role |
|---|---|---|
| Legacy REAPER entrypoint | `src/reaper_engine.py: PainReaperLocal` | spaCy sentence segmentation, pattern matching, gravity, clustering |
| spaCy initialization | `src/reaper_engine.py: load_nlp` | model load with blank-English/sentencizer fallback |
| Legacy pattern registry | `PainReaperLocal.patterns` | 11 inline keyword pattern definitions |
| Legacy normalization | `PainReaperLocal.detect` | sentence trimming and lowercase substring checks; no separate stage |
| Package detector entrypoint | `src/gravemark/detectors/marketplace_patterns.py` | line-based marketplace signal extraction |
| Package detector registry | `src/gravemark/detectors/__init__.py` | exports one detector |
| Source abstraction | `src/gravemark/sources/base.py` | `SourcePack.collect()` interface |
| Paste source | `src/gravemark/sources/paste_text.py` | wraps paste as one `EvidenceInput` |
| File sources | `local_file.py`, `pdf_file.py`, `csv_file.py` | local text/PDF/CSV ingestion |
| Evidence input model | `src/gravemark/models/evidence.py` | dataclass wrapper with source metadata |
| Legacy evidence dictionaries | `src/reaper_engine.py` | actual detected signal shape |
| Finding dataclass | `src/gravemark/models/findings.py` | narrow typed base shape; runner returns richer dicts |
| Score model | `src/gravemark/models/scores.py` | `ScoreResult` dataclass |
| Scoring registry | `src/gravemark/scoring/__init__.py` | profile resolution and migration aliases |
| Scoring profiles | `src/gravemark/scoring/*.py` | deterministic factor calculations |
| Grouping | `PainReaperLocal.cluster_and_score` | quote-prefix grouping only |
| Package aggregation | `src/gravemark/runs/runner.py` | no aggregation; one cluster per finding |
| Target profiles | `src/gravemark/targets/*.json` | data-driven watch/problem/tool terms |
| Run orchestration | `src/gravemark/runs/runner.py` | package pipeline and manifest |
| Run manifest | `src/gravemark/runs/run_manifest.py` | reproducibility/diagnostic metadata |
| AI client | `src/local_ai.py` | Ollama and OpenAI-compatible local HTTP calls |
| AI enrichment | `src/ai_enrichment.py` | append-only `local_analysis` enrichment |
| AI policy | `src/validation_policy.py` | prompt policy and warning checks |
| Prompts | `src/prompts.py`, `prompt_profiles.py` | strict analyst instructions |
| FastAPI legacy routes | `api.py:/detect*` | REAPER detection and file/url ingestion |
| FastAPI package route | `api.py:/gravemark/runs/market-scan` | package pipeline |
| FastAPI analysis routes | `api.py:/enrich`, `/report`, `/local-analysis/test` | optional analysis/reporting |
| React UI | `gravemark-dashboard/src/App.jsx` | broad internal operator console |
| Streamlit UI | `local_streamlit_app.py` | duplicate legacy local UI |
| Persistence | `api.py`, `gravemark_runs.db` | SQLite run history/latest state/diagnostics |
| Scraping/scout | `api.py`, `scout.py`, `scout_mode.py` | URL fetching, pagination planning, preview |
| MCP integration | `tools/gravemark-mcp/src/server.ts` | internal tool server around Gravemark |

## 5. KEEP / ADAPT / PRIVATE / DEAD Classification Table

| Component | Classification | Extraction decision |
|---|---|---|
| `PainReaperLocal` matching behavior | ADAPT | Preserve behavior, split pattern registry and output construction from UI/API concerns. |
| `load_nlp()` fallback | ADAPT | Keep fallback, but make model choice explicit and deterministic in the demo. |
| Legacy 11-pattern registry | KEEP | Small, inspectable, and central to the requested REAPER proof. |
| Legacy gravity calculation | KEEP | Deterministic and local; document its heuristic nature. |
| Legacy quote-prefix clustering | ADAPT | Preserve only if the demo proves grouping; replace collision-prone prefix identity with stable evidence IDs. |
| `EvidenceInput` | ADAPT | Add explicit provenance fields and avoid timestamp-only identity. |
| Legacy signal dictionary | ADAPT | Convert to a documented immutable Evidence contract. |
| `Finding` dataclass | ADAPT | Extend or replace with a contract that references evidence IDs. |
| `ScoreResult` | KEEP | Suitable small result object. |
| Scoring profile base/registry | KEEP | Useful deterministic seam; expose one default profile publicly. |
| `EvidenceQualityScoring` | KEEP | Closest to evidence-only scoring. |
| Other scoring profiles | ADAPT | Keep internally; expose only curated profiles in the reference demo. |
| Target JSON profiles | KEEP | Good repeatable fixture mechanism after sanitization. |
| `PasteTextSource` | KEEP | Directly supports the demo contract. |
| `CsvFileSource` | KEEP | Useful curated fixture input, if row provenance is retained. |
| Local/PDF source packs | ADAPT | Optional; preserve filename/page provenance or defer until tested. |
| `MarketplacePatternsDetector` | ADAPT | Useful separate detector, but not a substitute for REAPER/spaCy. Keep as an alternate fixture detector or exclude from the smallest demo. |
| `run_market_scan` | ADAPT | Reuse orchestration ideas, but remove UUID/time/persistence and wire real grouping/evidence references. |
| Run manifest | ADAPT | Keep stable profile and input summaries; exclude internal operational fields. |
| `ai_enrichment.py` | KEEP | Correct append-only architecture, subject to stronger schema validation. |
| `LocalAIClient` | KEEP | Small local-only adapter; default disabled and no cloud fallback. |
| `validation_policy.py` | KEEP | Preserve the evidence/analysis boundary and warnings. |
| `prompts.py` / prompt profiles | ADAPT | Sanitize and require evidence IDs in model context/output. |
| `/detect` and `/enrich` | ADAPT | Reduce to a small public API with separate deterministic and analysis operations. |
| React dashboard | ADAPT | Reuse evidence inspection concepts; do not extract the whole internal console. |
| `local_streamlit_app.py` | DEAD / STALE | Duplicate UI path with scraping and legacy assumptions; not the reference seam. |
| URL fetching/pagination/scout | PRIVATE | Explicitly outside public demo scope and introduces network variability and SSRF/privacy concerns. |
| SQLite history/latest state/diagnostics | PRIVATE | Persistence is out of scope and obscures repeatability. |
| Docker/deployment files | PRIVATE | Not required for a local reference implementation. |
| Gravemark MCP server | PRIVATE | Internal integration surface; unnecessary public architecture exposure. |
| Duplicate README status sections and legacy claims | DEAD / STALE | Documentation is inconsistent and should not define the extracted contract. |
| Broad dashboard pages such as Settings, Diagnostics, Prompts, Scout | PRIVATE | Internal operator workflows, not required to prove the core flow. |

## 6. Dependency Map

```text
source record
  -> source pack (paste/csv/file/pdf)
  -> [legacy: spaCy load -> sentence segmentation]
  -> deterministic pattern registry
  -> immutable Evidence objects + provenance
  -> deterministic scorer
  -> grouping/aggregation
  -> candidate finding (evidence_ids only)
  -> optional LocalAIClient
  -> local_analysis (notes only)
  -> serialized result / evidence inspector
```

Current coupling:

- `PainReaperLocal` owns spaCy initialization, patterns, scoring, source-field construction, timestamps, and detection output shape in one class.
- The new package path owns source selection, target resolution, scoring resolution, rendering, and manifest generation in `run_market_scan()`.
- The two paths use different pattern registries and different output schemas.
- `api.py` imports both paths and also owns SQLite schema, scraping, reporting, and operational logging.
- The frontend understands both `signals` and `findings`, and both legacy and package endpoint shapes.
- AI receives mutable cluster dictionaries and returns shallow copies; there is no formal schema preventing a caller from supplying fabricated evidence to `/enrich` beyond a presence check.

## 7. Current Data Contracts

### `EvidenceInput`

`src/gravemark/models/evidence.py` defines `EvidenceInput(source_id, source_type, content, metadata)`. `metadata` currently contains `origin`, a runtime `created_at`, `source_url=None`, and `filename=None`. Source packs may update `filename`; they do not consistently preserve page, row, or character offsets.

### Legacy detected signal

`PainReaperLocal.detect()` returns a dictionary with `signal_id`, `source_id`, `source_type`, `source_label`, `source_url`, `page_number`, `quote`, `pattern`, `matched_terms`, `gravity_score`, and `created_at`. `signal_id` is based on source ID and sentence index, so multiple patterns on one sentence collide.

### Package finding

The runner returns `finding_id`, `run_id`, `source_id`, `target_id`, `detector_id`, `finding_type`, `label`, `evidence_quote`, `source_location`, `confidence`, `gravity_score`, `risk_flags`, `tags`, `notes`, plus prices, tools, buyer hits, `score_factors`, `pattern`, `quote`, `frequency`, and `final_priority`. The `Finding` dataclass does not cover all fields actually returned.

### `ScoreResult`

`ScoreResult` contains integer `gravity_score`, string `verdict`, and integer-valued `factors`.

### AI result

`enrich_cluster()` preserves the cluster, optionally adds `detected_evidence` with patterns/quotes/sources/score, and adds `local_analysis` with status, profile, theme label, summary, hypothesis, fix notes, validation questions, missing evidence, risks, candidate-only marker, warnings, and raw model output. The implementation is structurally separate but not fully typed or immutable.

## 8. Proposed Demo Data Contracts

```json
{
  "source": {
    "source_id": "fixture_001",
    "source_type": "paste_text",
    "label": "Curated support excerpts",
    "text": "...",
    "provenance": {"fixture": "support_001.txt", "line_start": 1, "line_end": 1}
  },
  "detected_evidence": [
    {
      "evidence_id": "ev_fixture_001_000_01",
      "source_id": "fixture_001",
      "quote": "...",
      "pattern_id": "VERB_FAIL",
      "matched_terms": ["crash"],
      "location": {"sentence_index": 0, "start_char": 0, "end_char": 24},
      "deterministic_score": 5.2
    }
  ],
  "candidate_finding": {
    "finding_id": "finding_001",
    "title": "...",
    "supporting_evidence_ids": ["ev_fixture_001_000_01"],
    "score": 72,
    "score_factors": {"evidence_quality": 4},
    "rank": 1,
    "validation_required": true
  },
  "local_analysis": {
    "status": "ready",
    "theme_label": "...",
    "root_cause_hypothesis": "...",
    "candidate_fix_notes": "...",
    "validation_required": true,
    "source": "local_model",
    "based_on_evidence_ids": ["ev_fixture_001_000_01"]
  }
}
```

The API must reject or ignore AI-supplied evidence IDs, quotes, scores, and provenance. The deterministic stage owns `detected_evidence`, finding membership, and scores. The AI stage may only populate `local_analysis` fields and warnings.

## 9. Public / Private Boundary Recommendation

Use **a sanitized copy/subset plus a reduced reference implementation**. Direct module reuse is unsafe because the repository currently exposes both an internal operator console and network/persistence/MCP surfaces, and because the legacy and package contracts are not interchangeable.

The public subset should contain: one REAPER detector, spaCy initialization/fallback, explicit patterns, paste and fixture sources, immutable evidence schema, one deterministic scoring profile, stable grouping/ranking, a local AI adapter, strict analysis schema, two or three fixtures, and focused tests. Leave scraping, Scout, SQLite, MCP, broad configuration, production deployment, and internal diagnostics private.

## 10. Existing Test Coverage

Existing tests cover useful pieces:

- `test_reaper_engine_smoke.py` covers legacy deterministic detection.
- `test_spacy_model_fallback.py` covers fallback initialization.
- `test_local_ai_disabled.py`, `test_ai_json_parse.py`, and `test_ai_enrichment_contract.py` cover disabled AI, parsing, and preservation on failure.
- `test_evidence_bundle_contract.py` checks signal/source IDs, report limitations, and a basic evidence/analysis separation case.
- `test_gravemark_modules.py` covers target loading, profile migration, scoring profile shape, package runner output, source packs, and fingerprint stability.
- `test_gravemark_endpoint_contract.py`, `test_gravemark_phase2_contract.py`, `test_gravemark_phase5_contracts.py`, `test_api_contracts.py`, and `test_gravemark_contract_snapshots.py` cover route presence, run history, exports, failure responses, diagnostics, and snapshots.
- Dashboard tests cover selected UI contracts, review utilities, build info, and browser proof screenshots.

The tests are largely contract/snapshot tests around the internal system. They do not yet prove the complete requested public-demo chain with immutable Evidence objects and evidence IDs.

The attempted audit test run was blocked before collection: the configured Python environment's `pytest` failed with `ModuleNotFoundError: No module named 'iniconfig'`. No dependency installation was performed.

## 11. Missing Tests

Required public-demo tests:

1. Same input, same detector version, and same profile produce byte-equivalent deterministic evidence, excluding explicitly separate run metadata.
2. Each pattern match gets a unique evidence ID, even when multiple patterns match one sentence.
3. Source provenance—including fixture ID, row/page, sentence index, and quote offsets—survives source normalization, detection, grouping, ranking, and serialization.
4. Every candidate finding has at least one supporting evidence ID, and every referenced ID exists.
5. Scores can be recomputed from detected evidence and explicit deterministic factors only.
6. A fake AI response containing a new quote/pattern/source cannot modify evidence or score.
7. AI-disabled, unavailable, timeout, malformed JSON, and exception paths preserve deterministic findings.
8. AI output is isolated under `local_analysis` and is marked candidate-only/validation-required.
9. Empty, short, malformed, and no-match fixture inputs produce honest status and warnings.
10. Duplicate or near-duplicate quotes do not collapse unrelated sources through the current first-60-character key.
11. The public serialized contract contains no URLs, credentials, internal filesystem paths, database state, or private operational fields unless deliberately present as fixture provenance.

## 12. Missing Demo Components

- A single canonical public pipeline joining source normalization, REAPER detection, Evidence objects, grouping, ranking, and analysis.
- An explicit normalization function; current code only trims/splits and performs inline lowercasing.
- A first-class immutable Evidence model used by both the detector and API output.
- Stable evidence IDs and evidence references on findings.
- A real grouping contract for the package path, or a documented decision to show one finding per evidence group.
- A minimal curated fixture directory with expected deterministic JSON outputs.
- A small evidence inspector showing quote, pattern, score, and provenance beside each finding.
- A typed/validated local-analysis result that cannot carry authoritative evidence fields.
- A public-safe API/CLI that does not require SQLite, scraping, Docker, authentication, or cloud AI.

## 13. Recommended Build Order

1. Resolve the source checkout/path discrepancy and freeze the exact Gravemark revision being extracted.
2. Select the legacy REAPER behavior as the canonical deterministic detector for this demo; retain package marketplace detection as a separate internal reference only.
3. Extract patterns, spaCy initialization, normalization, and deterministic scoring into small modules without changing behavior.
4. Define immutable Evidence and provenance contracts with stable IDs and offsets.
5. Implement deterministic grouping and candidate findings by evidence ID; add recomputation and referential-integrity tests.
6. Add sanitized fixtures and golden deterministic outputs.
7. Add the local AI adapter and strict append-only `local_analysis` contract.
8. Add the smallest presentation surface: fixture selector, paste input, ranked findings, and evidence inspector.
9. Run the focused tests in a complete isolated environment and manually verify deterministic/no-AI/AI-failure states.

## 14. Demo Acceptance Criteria

- A user can select a curated local fixture or paste text.
- The UI/API visibly shows normalized source material and deterministic REAPER matches.
- Every displayed evidence item has a stable ID, quote, pattern, score, and source provenance.
- Ranked candidate findings link back to one or more evidence IDs.
- Changing or disabling local AI does not change deterministic evidence, grouping, ranking, or scores.
- AI notes are visibly separate, marked as hypotheses/candidate-only, and never become evidence.
- AI failure leaves the deterministic result usable.
- The same deterministic input produces the same evidence and ranking.
- No live scraping, authentication, persistence, cloud-only dependency, MCP, or private operational surface is required.
- Fixtures and focused tests are repeatable on a clean local Windows Python environment.

## 15. Risks / Coupling Issues

- **Two engines:** `src/reaper_engine.py` and `src/gravemark` have different semantics; extracting both would confuse the public contract.
- **No formal normalization stage:** behavior is embedded in sentence/line iteration and lowercase substring checks.
- **Evidence is not consistently a model:** `EvidenceInput`, legacy signal dictionaries, and package findings are separate shapes.
- **Provenance loss:** package detector rows preserve only `line:N`; source metadata is not copied into the finding contract comprehensively.
- **ID collisions/variability:** legacy IDs omit pattern identity; package run IDs use UUIDs; timestamps appear in source metadata and signals.
- **Weak grouping:** quote-prefix grouping can merge distinct records and does not produce stable group IDs.
- **AI input trust:** `/enrich` checks for evidence presence but accepts caller-supplied cluster content; a public API must derive evidence server-side or verify references.
- **Operational coupling:** `api.py` combines core detection with SQLite, URL fetching, reports, diagnostics, CORS, and broad route surface.
- **Frontend coupling:** `App.jsx` handles multiple endpoint generations and internal pages; it should not be copied wholesale.
- **Environment fragility:** spaCy model availability is optional, while the audit environment could not run pytest due to a missing `iniconfig` dependency.
- **Documentation drift:** README repeats “Honest Project Status” and describes both Streamlit and React/FastAPI as primary, so it cannot serve as the sole extraction specification.
