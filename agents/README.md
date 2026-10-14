# agents/

1 könyvtár = 1 agent = 1 Docker container = 1 Claude-session.

```
agents/<név>/
├── agent.yaml    # leíró: szerep, modell, skillek, tool-allowlist, MCP-k, üzenettípusok, egress, limitek, ütemezés, költségplafon
├── CLAUDE.md     # szerep / rendszerprompt
├── skills/       # az agent saját skilljei: skills/<skill>/SKILL.md
├── Dockerfile    # FROM auxin-agent-base + saját fájlok és függőségek
└── tests/
```

`agents/Dockerfile` a közös base image (`auxin-agent-base`): Python, pinelt függőségek, `libs/`, non-root user, healthcheck. Nem fut önállóan, az agent image-ek épülnek rá. Közös skill-könyvtár csak akkor lesz, ha tényleg megjelenik közös skill.
