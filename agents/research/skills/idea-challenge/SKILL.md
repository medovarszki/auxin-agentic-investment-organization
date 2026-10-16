---
name: idea-challenge
description: Challenge one investment idea with web, IBKR and knowledge-base research, then propose it (target price, horizon, risks, sources, conviction) or reject it with a reason.
---

# Idea challenge

## 1. Pin down the instrument
- `mcp__ibkr__get_contract` for the idea's conid: exchange, currency, industry, ISIN, stock vs ETF (`stock_type`). If the conid is missing or wrong, resolve it with `mcp__ibkr__search_contract`; if IBKR has no match, reject.
- `mcp__ibkr__get_price`: today's price (`last`, or the bid/ask mid). If it is `stale`, say so; the PM gate will re-check the price anyway.
- `mcp__ibkr__get_history` (6-12 months): trend, recent move, drawdowns. Reject chasing (a sharp run-up already pricing in the thesis).

## 2. Check the memory
`mcp__knowledge-base__get_company_history` (conid) and `mcp__knowledge-base__search` (ticker, theme): earlier ideas, rejections and lessons. If the fund rejected the same bet recently, only propose it on material new information, and name it.

## 3. Research the case
With WebSearch / WebFetch and `mcp__ibkr__get_news`:
- **Stock:** business and competitive position, latest results and guidance, balance sheet, valuation versus peers and history, suppliers / customers / partners that carry the thesis or its risk, upcoming catalysts (earnings date, product, regulation).
- **ETF:** what it holds (top holdings, sector weights), cost and size, what drives the basket, valuation of the basket.
- What would make the thesis wrong, and how likely is it?

## 4. Decide
Set a **target price** you can justify (valuation multiple, peer comparison, or scenario) and a **horizon** (2-60 weeks). Upside = (target - today's price) / today's price.

- **Propose** only if upside >= 15% and the case holds after the challenge. Fill:
  - `instrument`: conid, symbol, primary exchange, currency, `asset_class` (`stock` or `etf`), ISIN and industry if IBKR has them
  - `market_price` (today's IBKR price), `target_price`, `horizon_weeks`
  - `thesis`: one or two sentences
  - `risks`: at least 3 concrete risks
  - `sources`: at least 3 dated sources you retrieved (title, url, published_at)
  - `conviction` 1-5: 1 = speculative, 3 = solid case with open questions, 5 = exceptional, well-evidenced case with limited downside
  - `invalidation`: the observable event that would make you close the position
- **Reject** otherwise, with a concrete reason (e.g. "upside only 8% at 15x forward earnings", "thesis already priced in after +35% in 3 months", "no reliable source for the demand claim").
