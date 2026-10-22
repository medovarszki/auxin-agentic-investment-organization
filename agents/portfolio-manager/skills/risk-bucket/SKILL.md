---
name: risk-bucket
description: Classify the proposed instrument into one of 4 company-risk buckets (1 stable ... 4 speculative); the runtime caps every bucket at 25% of NAV.
---

# Risk bucket

Every decision (BUY or REJECT) carries a `risk_bucket` from 1 to 4: how risky the **company** (or the ETF's holdings) is, not how good the trade is. The runtime keeps each bucket at or below 25% of NAV (`portfolio-rules.yaml` `risk_bucket`) and sizes the BUY down, or rejects it, when the bucket is full. Buckets are how the fund spreads its risk, so classify honestly: a too-low bucket hides risk.

## Evidence
- `mcp__ibkr__get_contract`: industry, stock vs ETF.
- `mcp__ibkr__get_history` (1 Y, daily bars): rough annualised volatility and the largest drawdown.
- The proposal (thesis, risks, sources) and web knowledge: market cap, profitability, stage, debt, binary events.

## Buckets

| Bucket | Name | Typical company | Guide values |
|---|---|---|---|
| 1 | stable | Large, mature, steadily profitable, often a dividend payer (staples, utilities, healthcare majors); broad index ETFs (S&P 500, world) | market cap > 50 bn USD, beta < 0.8, annualised volatility < 20%, profitable for 5+ years |
| 2 | moderate | Established profitable company with market-like swings (large-cap tech, industrials, financials); sector ETFs | market cap > 10 bn USD, beta 0.8-1.2, volatility 20-30%, profitable |
| 3 | growth | Fast grower or deep cyclical, mid cap, thin or volatile profits (semis, software growth, commodities, emerging markets) | market cap 2-10 bn USD or beta 1.2-1.6, volatility 30-50%, profit unstable or just turned positive |
| 4 | speculative | Loss-making or early stage, small cap, recent IPO, story stock, binary outcome (clinical trial, approval, single contract), high debt | market cap < 2 bn USD or beta > 1.6, volatility > 50%, no sustained profit |

Rules:
- The guide values are hints; the company's character decides. When the signals disagree, take the **riskier** bucket.
- A single binary event (trial readout, regulatory decision, refinancing) or going-concern doubt -> bucket 4, whatever the size.
- ETFs: broad, diversified index -> 1; sector or factor ETF -> 2; single-country emerging market, thematic or commodity-miner ETF -> 3; leveraged or crypto-linked -> 4.
- Name the bucket and the one or two facts that decided it in the rationale (e.g. "bucket 3: 45% volatility, profit just turned positive").

## Fit
Check the bucket's current weight in the portfolio: the open positions' buckets are in the decision log (`mcp__knowledge-base__get_company_history` per conid: the BUY order's summary says `risk bucket N`; positions bought before this rule have none and do not count). If the bucket is nearly full, the runtime will size the BUY down; REJECT if a small position would not be worth it.
