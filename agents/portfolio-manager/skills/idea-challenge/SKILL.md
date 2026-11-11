---
name: idea-challenge
description: Decide on one Research idea: check the portfolio fit first, then challenge the case with web, IBKR and knowledge-base research, and BUY (with target price, horizon, risks, sources, conviction) or REJECT with a reason.
---

# Idea challenge

## 1. Portfolio fit first
Reject early, before the full research, when the idea cannot fit the portfolio as it is now:
- `mcp__ibkr__get_positions` and `mcp__ibkr__get_account_summary`: is there free cash? Would it double an existing bet (same company, same industry, an overlapping ETF, the same macro driver)?
- **Risk bucket:** classify the instrument with the `risk-bucket` skill and check the bucket's room. A full or nearly full bucket is a REJECT ("bucket 4 holds 24% of NAV").
- **Memory:** `mcp__knowledge-base__get_company_history` (conid), `mcp__knowledge-base__get_recent_rejections` and `mcp__knowledge-base__search` (ticker, theme): was the same bet rejected or closed with a loss recently? Only go on with material new information, and name it.
- **Re-proposal:** when the idea has a `prior_rejection` (the instrument is in cooldown), check its `revisit` first: are the new sources real and dated after the rejection, and does `what_changed` answer the rejection reason and the `reconsider_if`? If not, REJECT early ("nothing material changed since the rejection on ...").

## 2. Pin down the instrument
- `mcp__ibkr__get_contract` for the idea's conid: exchange, currency, industry, ISIN, stock vs ETF (`stock_type`). If the conid is missing or wrong, resolve it with `mcp__ibkr__search_contract`; if IBKR has no match, reject. The fund only buys USD-quoted instruments for now (no FX): reject any other currency.
- `mcp__ibkr__get_price`: today's price (`last`, or the bid/ask mid). If it is `stale`, say so; the runtime gate re-checks the price anyway.
- `mcp__ibkr__get_history` (6-12 months): trend, recent move, drawdowns. Reject chasing (a sharp run-up already pricing in the thesis).

## 3. Challenge the case
Look for the arguments against the idea, not only for it. With WebSearch / WebFetch and `mcp__ibkr__get_news`:
- **Stock:** business and competitive position, latest results and guidance, balance sheet, valuation versus peers and history, suppliers / customers / partners that carry the thesis or its risk, upcoming catalysts (earnings date, product, regulation).
- **ETF:** what it holds (top holdings, sector weights), cost and size, what drives the basket, valuation of the basket.
- What would make the thesis wrong, and how likely is it?

## 4. Decide
Set a **target price** you can justify (valuation multiple, peer comparison, or scenario) and a **horizon** (2-60 weeks). Upside = (target - today's price) / today's price.

- **BUY** only if upside >= 15%, the case holds after the challenge and it fits the portfolio. Fill the `proposal`:
  - `instrument`: conid, symbol, primary exchange, currency, `asset_class` (`stock` or `etf`), ISIN and industry if IBKR has them
  - `market_price` (today's IBKR price), `target_price`, `horizon_weeks`
  - `thesis`: one or two sentences
  - `risks`: at least 3 concrete risks
  - `sources`: at least 3 dated sources you retrieved (title, url, published_at)
  - `conviction` 1-5: 1 = speculative, 3 = solid case with open questions, 5 = exceptional, well-evidenced case with limited downside; the runtime sizes the BUY by it
  - `invalidation`: the observable event that would make the fund close the position
- **REJECT** otherwise, with the concrete reason in one or two sentences (e.g. "bucket 3 is full", "upside only 8% at 15x forward earnings", "thesis already priced in after +35% in 3 months", "no reliable source for the demand claim"), so Research can learn from it. Also set:
  - `reject_basis`: `thesis` (the case, valuation or portfolio fit failed: the instrument goes into a cooldown) or `data` (only missing / unreliable data blocked you, e.g. a stale IBKR price, and the case itself could pass: no cooldown). If both apply, it is `thesis`.
  - `reconsider_if`: the concrete, observable change that would reopen it (e.g. "a live quote below $60", "Q3 orders back above 1.0 book-to-bill", "risk bucket 3 below 20% of NAV"). Research must answer this to re-propose the instrument within the cooldown.
