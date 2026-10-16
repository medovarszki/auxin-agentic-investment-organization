---
name: position-review
description: Re-evaluate one open position of the fund from scratch (thesis, price, news, valuation, risks) and recommend HOLD, REDUCE (with a target weight) or CLOSE.
---

# Position review

The fund holds the position below. Judge it as if you had to buy it again today: the past entry price is not a reason to hold or to sell.

## 1. The original case
From the request: `entry.proposal` (thesis, target price, horizon, risks, invalidation, conviction) and `entry.order` (when and how much was bought). If `entry` is empty, the fund has no recorded thesis: build today's case from scratch. Check `mcp__knowledge-base__get_company_history` (conid) for earlier reviews and lessons.

## 2. What changed
- `mcp__ibkr__get_price` and `mcp__ibkr__get_history` (since the entry, and 6-12 months): the move versus the target price.
- `mcp__ibkr__get_news` and WebSearch / WebFetch: results, guidance, analyst changes, sector and macro news since the entry or the last review.
- Did the invalidation event happen? Did any listed risk materialize? Is the thesis playing out, delayed, or broken?

## 3. Decide
Compute today's upside to a target price you would defend now (it may differ from the original one).

- **HOLD:** the thesis holds and the remaining upside still justifies the position size.
- **REDUCE** with `target_weight_pct` (below the current `holding.weight_pct`): the case is weaker or most of the upside is realized, but not broken; or the position grew too large. Typical sizes by conviction: 1-5 -> 2 / 4 / 6 / 8 / 10% of NAV.
- **CLOSE:** the thesis is broken, the invalidation event happened, the target is reached with little upside left, or a clearly better use of the capital is obvious.

There is no stop-loss rule: a price drop alone is not a reason to sell, and a gain alone is not a reason to hold. A position bought only days ago is normally a HOLD unless something material changed; say so briefly instead of repeating the full research.

Give a `rationale` of a few sentences (what changed, today's target and upside, why this decision) and the dated `sources` you used (at least one for any news you cite).
