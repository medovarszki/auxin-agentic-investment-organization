---
name: narrative-and-sentiment
description: Turn the market scan into a sentiment call (risk_on / neutral / risk_off) and the 1-3 narratives dominating the market. Use after market-scan.
---

# Narrative and sentiment

**Sentiment** is one of:
- `risk_on`: equities rising broadly, volatility low or falling, credit and cyclicals leading.
- `risk_off`: equities falling, volatility rising, flight to bonds, gold, defensive sectors or the dollar.
- `neutral`: mixed or range-bound signals.

Base the call on at least three signals from the scan (e.g. index trend, VIX level and direction, yields, sector leadership) and list them as `key_indicators`, each with its value and date.

**Dominant narratives** are the 1-3 stories the market is trading on (e.g. "rate cuts arriving faster than expected", "AI capex boom", "China stimulus"). For each, check that several independent sources discuss it in the last week; a story in one article is not a narrative.

Write a `summary` of 3-6 sentences a portfolio manager can read in 30 seconds.
