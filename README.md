# Gravemark Reference

This repository demonstrates deterministic extraction of evidence-backed pain signals and candidate findings from qualitative source material.

```text
Source → normalization → REAPER → Evidence → scoring → grouping → Candidate Findings
```

The core invariant is simple: Evidence is created only by deterministic detection. Phase 1 contains no AI-generated fields. AI interpretation may be added later only as a separate optional layer under `local_analysis`.

## Deterministic Evidence vs. Optional Local Analysis

Evidence and candidate findings are deterministic and authoritative. Optional local analysis can interpret only the Evidence explicitly supporting one finding. AI output is not evidence, requires validation, and cannot change evidence, scores, ranking, provenance, or finding membership. Phase 2 analysis is disabled unless a local endpoint and model are configured.

This is a small reference implementation, not the full internal Gravemark system. It does not include live scraping, production ingestion, autonomous outreach, cloud AI, authentication, multi-user support, persistent databases, UI, or internal Gravemark functionality.

## Run

```powershell
python -m pip install -e ".[test]"
python -m pytest
```

The canonical entrypoint is `gravemark.pipeline.run_pipeline()`. Fixtures and a golden result are under `fixtures/`.
