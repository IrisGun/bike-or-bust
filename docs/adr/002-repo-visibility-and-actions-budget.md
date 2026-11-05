# ADR-002: Repo visibility and GitHub Actions budget

- Date: 2026-11-05
- Status: [Proposed] (action needed: make the repo public)
- Author: [Jamie]

## Context
The collector runs on GitHub Actions (cron). Whether the repo is public or private decides how much
runner time is free. ADR-001 keeps raw data out of the repo, so visibility does not affect the
Citi Bike licence: the repo holds code, docs and tiny synthetic fixtures only.

Limits (GitHub docs, checked 2026-11-05):
- GitHub Free, private repos: $12/month of included compute, not a fixed number of minutes. Linux
  2-core runner costs $0.006/minute, rounded **up to a whole minute per job** ($12 is about 2,000 min).
- Public repos: standard GitHub-hosted runners are free.
- Scheduled workflows: shortest interval 5 minutes; may be delayed under load and queued jobs may be
  dropped; in a public repo they are **disabled after 60 days without repository activity**.
- A single job can run up to 6 hours.

## Options
| Cadence | Jobs/day | Minutes/month | Cost in a private repo |
|---|---|---|---|
| Hourly cron | 24 | ~720 | ~$4.3, within the $12 |
| 15-minute cron | 96 | ~2,880 | ~$17, over the $12 |
| Looping job (1-min polling, up to 6 h per job, 24/7) | 4 | ~43,200 | ~$259, far over; only ~33 h of dense collection fit in $12 |

## Decision
Make the repo **public**. It is a portfolio project, the repo contains no Citi Bike data, and public
repos get unlimited free runner time, which the 15-minute and dense-collection phases need.

## Consequences
- Never put secrets or data in the repo; storage credentials live in GitHub Secrets (ADR-001).
- Before going public: revoke and replace the personal access token that is embedded in the local
  `origin` URL, and review the commit history for anything sensitive.
- The cron is disabled after 60 days of no repo activity: keep commits flowing or add a keep-alive
  and a monitor that alerts on missing slots.
- Cron delays and dropped runs create gaps in collection; record them as known gaps.
- If the repo must stay private, the fallback is hourly cron only (about $4/month of the free quota),
  which cannot answer the sampling-frequency questions in the problem statement.
