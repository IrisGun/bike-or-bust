# ADR-002: Repo visibility and GitHub Actions budget

- Date: 2026-11-05
- Status: [Accepcted]
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

## Update 2026-11-17: the GitHub schedule did not fire
**Observed.**
- The repo is public and the cron schedule defined by no scheduled job run, while manual `workflow_dispatch` runs succeeded and wrote to R2.
- Ruled out: cron syntax, disabled workflow, Actions policy, fork or archived repo, committer permissions.

**Similar reports** (all unresolved or only partly resolved):
- [community/discussions/213232](https://github.com/orgs/community/discussions/213232): public repo, same symptom
  and the same cron string; the author moved to an external trigger.
- [community/discussions/185024](https://github.com/orgs/community/discussions/185024): staff linked it to a
  server-side flag affecting newly created schedules; but reports of the problem continue through October 2026.
- [community/discussions/201738](https://github.com/orgs/community/discussions/201738): daily cron delayed 8 to
  14 hours, one run dropped.

**Decision (for now).**
- Keep the schedule as it is and do not build a workaround yet.
- If the schedule still does not fire after the EDA on the existing snapshots, add an external scheduler (for example a Cloudflare Workers Cron Trigger) that calls `workflow_dispatch` through a fine-grained GitHub token.
- Not decided yet which service to use.
- Superseded on 2026-11-18 by [ADR-003](003-scheduling-github-cron-vs-airflow.md): the schedule turned out to drop ~97% of runs, so the external trigger is tried now instead of after the EDA.

**Consequence.**
- Cron delays and dropped runs create gaps in collection; record them as known gaps.
- Missed slots cannot be recovered (the feed only shows the present), so the time series will have gaps until this is fixed.
