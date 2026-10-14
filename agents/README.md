# agents/

1 könyvtár = 1 agent = 1 Docker container = 1 Claude-session.

```
agents/<név>/
├── agent.yaml    # leíró: szerep, modell, skillek, tool-allowlist, MCP-k, üzenettípusok, egress, limitek, ütemezés, költségplafon
├── CLAUDE.md     # szerep / rendszerprompt
├── skills/       # az agent saját skilljei: skills/<skill>/SKILL.md
├── Dockerfile    # FROM _base + saját skillek és függőségek
└── tests/
```

`_base/` a közös base image (non-root user, runtime, OTel). Közös skill-könyvtár csak akkor lesz, ha tényleg megjelenik közös skill.
