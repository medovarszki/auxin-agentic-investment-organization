---
name: proposal-review
description: Review one Research buy proposal against its evidence, the current portfolio and the fund's memory, and decide BUY or REJECT with a rationale.
---

# Proposal review

1. **Price check:** `mcp__ibkr__get_price` for the conid. If today's price already erased most of the upside to the target, REJECT (the runtime would reject below 15% anyway).
2. **Evidence:** are there at least 3 dated, relevant sources? Do the thesis, the target price and the horizon follow from them? Are the risks specific to this instrument (not generic)? Is the invalidation observable?
3. **Instrument:** `mcp__ibkr__get_contract`: does the instrument match the thesis (right listing, stock vs ETF, industry)?
4. **Portfolio fit:** `mcp__ibkr__get_positions` and `mcp__ibkr__get_account_summary`. Would this double an existing bet (same industry, overlapping ETF, same macro driver)? Is there free cash?
5. **Risk bucket:** classify the instrument with the `risk-bucket` skill and check the bucket's room in the portfolio.
6. **Memory:** `mcp__knowledge-base__get_company_history` (conid) and `mcp__knowledge-base__search` (ticker, theme). Was a similar bet rejected or closed with a loss before, and does the proposal answer that?

Decide:
- **BUY** when the case is evidenced, the upside is real at today's price and it fits the portfolio. The runtime then sizes it by the conviction.
- **REJECT** otherwise, with the concrete reason in one or two sentences.
