# ADR-003: Scheduling the collector: GitHub cron, Airflow, or an external trigger

- Date: 2026-11-18
- Status: Proposed
- Author: [Jamie]

## Context
The collector must run every 15 minutes. GitHub Actions cron is free in a public repo and needs no server, but in about 19 hours only 2 of the ~78 expected scheduled runs started (~97% dropped); the ones that did run were only ~6 minutes late, and dropped runs raise no error. The cause is unknown (GitHub documents scheduled runs as best-effort; see ADR-002). Manual dispatch runs work, so the collector itself is fine.

## Options
| Criterion | GitHub Actions cron | Airflow (self-hosted) |
|---|---|---|
| Retry | None for a failed job; the collector retries HTTP itself | Per-task retries with delay |
| Backfill | None; a missed tick is gone | Built in, by data interval |
| Infrastructure | None | Scheduler, web server, metadata DB; ~4 GB RAM; a machine that is always up |
| Cost | $0 in a public repo | Software is free; reliable free hosting is not (see below) |
| Passing data between tasks | Files in object storage; artifacts only within one workflow | XCom for small values; files for large data |
| Dependencies | `needs:` inside one workflow only | Full DAG, sensors, trigger rules |
| Monitoring | Run list only; a missing run raises no alert | UI and alerts on failed or late runs |

Free Airflow hosting: Oracle Cloud Always Free is the only option with enough memory, but its allowance reportedly changed in 2026 and the card requirement is unconfirmed. The local machine is free but not always on.

## The deciding fact
GBFS is a snapshot source: it shows only the present, so a missed tick cannot be recovered by any tool, Airflow included. Backfill only helps when the source has history (trip files, weather archive) or when re-running from stored bronze data. For collection we need a reliable trigger, not an orchestrator.

## Decision
1. Keep the collector and `collect.yml`, and add an external scheduler that calls the GitHub API (`workflow_dispatch`, fine-grained token limited to this repo). Measure it for 24 hours. Keep the GitHub schedule as a fallback; duplicates are harmless because the collector is idempotent per slot.
2. The service is chosen at implementation time (for example a Cloudflare Workers Cron Trigger).
3. Use Airflow or Dagster locally for silver, gold, training and predict, where backfill works. Not decided here.
4. Add a check that counts missing slots, so a dropped trigger is visible.

Rule of thumb: if a missed run can be recovered from stored data, invest in idempotency and backfill; if not, invest in the trigger.

## Consequences
- Slots lost before the new trigger works are gone; list them in the README known gaps.
- The trigger adds one secret and one more part to keep running.
- If it is also unreliable, the fallbacks are a looping job or a small always-on host, which needs a cost decision first.
