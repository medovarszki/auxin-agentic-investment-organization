Decide on the investment idea below (JSON from the Research analyst's market scan, or entered by hand by the operator: `"origin": "manual"`) with the idea-challenge skill, and classify the instrument with the risk-bucket skill. Check the portfolio fit first: reject early, without the full research, when the idea does not fit.

Return `decision` (BUY or REJECT), the `rationale`, the `risk_bucket` (1-4) and, for a BUY, the `proposal`.

A manual idea gets exactly the same challenge and the same bar as a Research idea: the operator's conviction is not evidence. It may come without sources or background (the fields can be empty); do the research yourself and fill the proposal's sources from what you retrieved. The instrument's conid is resolved by IBKR, but check it as usual.
