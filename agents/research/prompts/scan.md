Run today's market scan.

1. Use the market-scan skill to collect the current state of global markets.
2. Use the narrative-and-sentiment skill to make your sentiment call and name the dominant narratives.
3. Use the idea-generation skill to propose 0-3 ideas, each resolved to an IBKR conid with the ibkr tools.
   Skip anything the fund already holds. An instrument in cooldown (listed below, if any) only comes again with a
   `revisit` that shows what materially changed since the rejection (see the skill). If the scan has a risk-bucket
   focus (a section at the end, if any), propose only instruments from that bucket.

Return the result as the structured output (market_view and ideas).
