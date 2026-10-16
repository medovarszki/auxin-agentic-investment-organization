---
name: idea-generation
description: Derive 0-3 long-only stock or ETF ideas from the current narratives for a weeks-to-a-year horizon. Use after narrative-and-sentiment.
---

# Idea generation

For each dominant narrative, ask: who benefits for longer than a few days, and is that not yet fully priced in?

Good ideas:
- Follow from a narrative through a clear mechanism (e.g. rate cuts -> lower funding costs -> small-cap banks).
- Name one instrument precisely, resolved at Interactive Brokers (see below). Prefer the primary listing.
- Have a thesis that could be wrong in a checkable way.

Avoid:
- Instruments that already rose sharply on the news in the last days (chasing).
- Micro-caps and illiquid listings.
- Leveraged, inverse or thematic ETFs with tiny assets.
- Two ideas that are the same bet.

## Resolve every instrument at IBKR

The fund trades through Interactive Brokers, so an idea is only usable with an IBKR conid.

1. `mcp__ibkr__search_contract` with the ticker (or the company name). Pick the stock or ETF on its primary exchange in its home currency.
2. Fill `instrument.conid`, `instrument.exchange` (the primary exchange) and `instrument.currency` from that match.
3. `mcp__ibkr__get_price` for the conid: it confirms the instrument is tradable and gives today's price. If the price is `stale`, say so in the rationale. Use `mcp__ibkr__get_history` to check the recent move (no chasing).
4. If IBKR has no match, drop the idea; do not guess a conid.

## Skip what we hold or recently rejected

Before you finalize the list:

1. `mcp__ibkr__get_positions`: drop any idea whose conid the fund already holds.
2. `mcp__knowledge-base__get_recent_rejections` (30 days): drop any idea whose conid (or the same bet) was rejected,
   unless there is material new information since the rejection. Then name that information, with its dated
   source, in the rationale and say why it answers the rejection reason.
3. Optional: `mcp__knowledge-base__get_company_history` or `mcp__knowledge-base__search` to see what the fund
   already concluded about an instrument or theme.

At most 3 ideas per scan.

For each idea give: `thesis` (one sentence), `rationale` (why now, what could go wrong), and at least one dated source. Research will challenge every idea, so be honest about weak points.
