---
name: lesson
description: Turn the result of one closed position into a short, reusable lesson for the fund's knowledge base.
---

# Lesson from a closed position

The request holds the realized result of a closed position (cost, proceeds, commission, return, holding period).

1. `mcp__knowledge-base__get_company_history` (conid): the whole story of the position: the idea, the proposal (thesis, target price, horizon, risks, invalidation, conviction), the daily reviews and the orders.
2. Compare the plan with what happened:
   - Did the thesis play out, fail, or was the position closed for another reason (target reached, invalidation event, a better use of capital)?
   - Was the target price realistic? Was the conviction (and so the size) right in hindsight?
   - Which risk materialized; was it listed at entry? Did the reviews react in time, too early, or too late?
   - Use `mcp__ibkr__get_history` if the price path since the entry helps the judgement.
3. Separate skill from luck: a good result from a broken thesis is not a good decision, and a loss on a sound, well-sized bet is not necessarily a mistake.

Write the `lesson` in 2-4 sentences: what happened versus the plan, and one concrete, reusable rule for future ideas, proposals or reviews (e.g. "For cyclical ETFs, a 15% target in under 8 weeks was too ambitious: require a catalyst with a date"). No generic advice, no repetition of the numbers you were given.
