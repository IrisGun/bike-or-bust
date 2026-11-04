# ADR-000: [Data source decision]

**Date:** 2026-11-04
**Status:** [Initialized]
**Author(s):** [Jamie]

---
## 1. Context
_"Can I call-dib on a bike today to ride home"_
In Seoul, it depends on Ddareungi. Which mean this project is ideally initialized from this place.
However, based on the [feedback](https://data.seoul.go.kr/dataList/OA-15493/A/1/datasetView.do) API users of Seoul, it's decided to better start from other source.
So let's pick the biggest city on Earth with a pretty stable API to start with --> New York City

## 2. Decisions
1. Start this project with [Citi Bike GBFS](https://gbfs.citibikenyc.com/gbfs/gbfs.json) not Seoul Ddareungi (revisit later)
2. Let's first go with [v1.1](https://gbfs.lyft.com/gbfs/1.1/bkn/en/station_status.json)

## 3. Consequences
- No API key, no published rate limit (feed ttl is 60 s; poll every 15 min).
- Source may change or stop at any time (Data Sharing Policy) - listed as a known gap.
