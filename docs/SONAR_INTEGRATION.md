# SonarQube Integration (Context7 & Background Scanner) 🔍

This document explains how Trinity integrates SonarQube results into the Context7 layer and how to enable a background scanner to keep Sonar context up-to-date.

## Overview
- Trinity fetches Sonar issues (best-effort, using `SONAR_API_KEY`) and attaches a concise summary to `state['retrieved_context']` when DEV-mode operations start.
- If MCP-based Context7 (`context7-docs`) is available, Trinity will index a structured Sonar analysis document into the Context7 docs store (preferred). Otherwise it falls back to local `Context7.add_document()`.
- A background scanner can optionally run periodically to keep Sonar context fresh.

## Environment Variables
- `SONAR_API_KEY` (required for Sonar API access)
- `SONAR_URL` (default: `https://sonarcloud.io`)
- `SONAR_PROJECT_KEY` (optional override; Trinity also reads `sonar-project.properties` in repo root)
- `TRINITY_SONAR_BACKGROUND=1` (enable background scanner)
- `TRINITY_SONAR_SCAN_INTERVAL` (minutes, default: `60`)

## How it works
1. At DEV task start, Trinity calls `_enrich_context_with_sonar()` which:
   - Fetches Sonar issues via the Sonar API
   - Attempts to index a rich, structured document using `SonarQubeContext7Helper.index_analysis_to_context7()` (prefers `context7-docs`) and attaches a pointer to `state['retrieved_context']`
   - If MCP Context7 is not available, it appends a compact summary and stores a local Context7 doc via `Context7.add_document()`
2. If `TRINITY_SONAR_BACKGROUND=1` is set, Trinity starts a background scanner (`core/sonar_scanner.py`) that periodically runs `runtime._enrich_context_with_sonar()` and re-indexes results.

## Security
- Keep `SONAR_API_KEY` in environment only and do not commit it. Trinity will not log API keys.

## Troubleshooting & Testing
- To test locally without enabling the background scanner, call: (Python)
  ```py
  from core.trinity import TrinityRuntime
  rt = TrinityRuntime(verbose=True)
  rt._enrich_context_with_sonar({"is_dev": True, "retrieved_context": "", "original_task": "Test Sonar"})
  ```
- To run the scanner once:
  ```py
  from core.sonar_scanner import SonarBackgroundScanner
  scanner = SonarBackgroundScanner(rt, interval_minutes=1)
  scanner.run_once()
  ```

## Notes
- All Sonar operations are best-effort and will not break Trinity if Sonar is not available or API keys are missing; Trinity will fallback to local storage or skip enrichment.
