---
name: idea-generation
description: Derive 0-3 long-only stock or ETF ideas from the current narratives for a weeks-to-a-year horizon. Use after narrative-and-sentiment.
---

# Idea generation

For each dominant narrative, ask: who benefits for longer than a few days, and is that not yet fully priced in?

Good ideas:
- Follow from a narrative through a clear mechanism (e.g. rate cuts -> lower funding costs -> small-cap banks).
- Name one instrument precisely, resolved at Interactive Brokers (see below). Prefer the primary listing.
- Trade in USD: for now the fund only buys instruments quoted in its base currency (USD, no FX conversion). A non-US
  company qualifies only through a USD listing (e.g. an ADR); otherwise drop it.
- Have a thesis that could be wrong in a checkable way.

Avoid:
- Instruments that already rose sharply on the news in the last days (chasing).
- Micro-caps and illiquid listings.
- Leveraged, inverse or thematic ETFs with tiny assets.
- Two ideas that are the same bet.

## Resolve every instrument at IBKR

The fund trades through Interactive Brokers, so an idea is only usable with an IBKR conid.

1. `mcp__ibkr__search_contract` with the ticker (or the company name). Pick the stock or ETF on its primary exchange in USD (a US listing or ADR).
2. Fill `instrument.conid`, `instrument.exchange` (the primary exchange) and `instrument.currency` from that match.
3. `mcp__ibkr__get_price` for the conid: it confirms the instrument is tradable and gives today's price. If the price is `stale`, say so in the rationale. Use `mcp__ibkr__get_history` to check the recent move (no chasing).
4. If IBKR has no match, drop the idea; do not guess a conid.

## Skip what we hold or recently rejected

Before you finalize the list:

1. `mcp__ibkr__get_positions`: drop any idea whose conid the fund already holds.
2. **Instruments in cooldown** (listed at the end of the task prompt; the Portfolio Manager rejected them on the
   merits recently): drop the idea, unless something material changed since the rejection that answers its
   `reason` or `reconsider_if`. A changed market mood can be such a change, but only with evidence that the change
   reaches this instrument. Then fill the idea's `revisit`:
   - `rejected_idea_id`: exactly as listed;
   - `what_changed`: what is new since `rejected_on` and why it answers the rejection;
   - `sources`: at least `min_new_sources` dated sources published **after** `rejected_on`.
   Without a valid `revisit` the runtime drops the idea; do not spend a slot on a repeat with nothing new.
   Rejections because of a portfolio rule or missing data (e.g. no live price) are not listed: those instruments
   may come again whenever they fit.
3. Same bet: `mcp__knowledge-base__get_recent_rejections` (30 days) also shows rejected ideas of other instruments;
   do not re-propose the same bet through a different ticker without the same kind of new information.
4. Optional: `mcp__knowledge-base__get_company_history` or `mcp__knowledge-base__search` to see what the fund
   already concluded about an instrument or theme.

## Risk-bucket focus

A scan can be started for one risk bucket (1 stable, 2 moderate, 3 growth, 4 speculative); the task prompt then ends
with a "Risk-bucket focus" section that holds the bucket definitions. In that case:
- The market view and narratives stay unfocused; only the ideas are limited to the bucket.
- Propose only instruments that belong in that bucket by the definitions; on the border the riskier bucket counts.
- The "Avoid" list above still applies: bucket 4 means small or early-stage companies, not micro-caps or illiquid
  listings.
- Name the bucket and the one or two deciding facts in the rationale. Zero ideas is a valid answer.

At most 3 ideas per scan.

For each idea give: `thesis` (one sentence), `rationale` (why now, what could go wrong), and at least one dated source. The Portfolio Manager challenges every idea against the portfolio, so be honest about weak points.
