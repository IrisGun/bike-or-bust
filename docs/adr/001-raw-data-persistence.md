# ADR-001: Where raw collector data is persisted

**Date:** 2026-11-04
**Status:** [Accepted] (direction); stoarage backend pending - see Open question
**Author(s):** [Jamie]

---

## 1. Context
- GitHub Actions runners are ephemeral, so the collector must push snapshots somewhere.
- The Citi Bike Data Sharing Policy forbids hosting, publishing or distributing the Data "as a stand-alone dataset"; analyses and reports using it as source material for non-commercial purposes are allowed.

## 2. Decision
- Raw snapshots are never committed to this repo and never stored anywhere publicly readable
  (no branch of a public repo, no public Actions artifacts, no public bucket).
- Raw/silver/gold data lives in a private location only.
- Published in the public repo: code, docs, charts, small aggregates, metrics, tiny synthetic test fixtures.

## 3. Open questions
- Backend: private data repo with daily-compacted files vs free private object storage (R2/B2).
- Current free-tier limits must be checked before choosing; to be recorded here.
