# Problem statement

- Status: draft
- Date: 2026-11-ish
- [Architecture Decision records (ADR)](adr/)

## 1. Decision this supports
_Official announment:_
A rebalancing crew has a limited number of trucks and stops per shift. They need to know which
stations to restock *first*.

_My actual agenda:_
I want an logistic-related problem to showcase in the porfolio. This intuitive approach could apply for various other interesting topics, such a demand forcasting, inventory optimization, resource allocation... One rabbit hole at a time.
`#logistics` `#optimization`

## 2. Prediction question
For station *s* at time *t*: what is the probability that the station runs out of bikes at some point
in the next 60 minutes?

Stock-out = `num_bikes_available = 0` while the station is installed and renting.

## 3. Project success definition
Not generic accuracy. The crew can visit only *k* stations, so the metric is precision@k: of the *k*
stations ranked highest, how many really ran out. The model must beat two baselines:

1. Persistence: "out of bikes now, so still out in 60 min".
2. Historical rate: the station's own stock-out frequency for that hour of the week.

If it does not beat both, the project has no value regardless of pipeline quality.

_My defensive words:_ Defo possesses its own value, at least a good pipeline quality proves a decent Data Engineer/Analytics Enigneer though. But let's better make it works.

## 4. Open choices (current defaults)
| # | Choice | Default | Why |
|---|--------|---------|-----|
| 1 | Label window | Any time within the next 60 min (not only at minute 60) | The crew cares whether the station runs out, not its state at one instant |
| 2 | E-bikes | Count total `num_bikes_available`; state the assumption | Simplest; revisit after EDA |
| 3 | Scoring cadence | Hourly | Dispatch shifts do not change faster; also bounds the data resolution needed |
| 4 | Scope | All hours, then analyse by time of day | Avoid choosing a biased scenario before seeing data |

## 5. Questions for EDA (derived from the above)
Sampling frequency (15 min, 1h, 6h...) is a consequence of these, not a spontanoues no brain choice:

1. How long does a stock-out last? If most last a few minutes, 15-min sampling misses many and the labels will be incomplete and biased.
2. Can the crew react in time? If stock-outs recover on their own within ~10 min, a 60-min forecast has little value.
3. How many stations run out often enough to learn from?
4. Is the data biased by time of day or day of week?
5. How often do values change between consecutive snapshots (feed ttl is 60 s)?
6. Any insights for a new station equipment needed?

## 6. Not decided yet
Storage backend (ADR 001), collection cadence, label sampling rules. These follow the EDA answers.
