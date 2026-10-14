# Execution agent

Kizárólag a jóváhagyott vételi és eladási megbízások végrehajtása IBKR connectoron, és a teljesülés visszajelzése. Az egyetlen agent IBKR írási joggal. Ár nélkül visszadobja a megbízást. Az IBKR-t az [ibkrfacade](https://github.com/medovarszki/ibkrfacade) REST-en át éri el, az `mcp-servers/ibkr` szerveren keresztül.

Leíró: [`agent.yaml`](agent.yaml). Szerepleírás: [`docs/ORG.md`](../../docs/ORG.md).
