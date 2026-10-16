# CLAUDE.md – a repó fejlesztéséhez

Ez a fájl a repón dolgozó fejlesztő-sessionöknek szól, nem a futó agenteknek (azok promptja: `agents/<név>/CLAUDE.md`).

## Kezdés
- Olvasd el a `docs/ORG_PROGRESS.md`-t: döntési napló, kész fázisok, nyitott kérdések, következő lépés.
- Fázisonként haladunk; egy fázis végén frissítsd az ORG_PROGRESS.md-t.
- A `README.md` „Szervezeti modell” fejezete a szervezet naprakész leírása (egységek, pozíciók, folyamatok, szabályok, ellenőrzési pontok): minden szerep-, folyamat- vagy szabályváltozással együtt frissítsd (Mihály kérése, 2026-10-16).
- MVP készül: döntési opcióknál az implementációban legegyszerűbbet javasold elsőnek.

## Szabályok
- Kommunikáció: tömör, magyar nyelvű, technikai kifejezések angolul.
- Git: közvetlenül a `main` branchre dolgozunk, nincs feature branch (Mihály döntése, 2026-10-14).
- Mellékhatás előtt kérdezz: csomagtelepítés, hálózati hívás, docker build/run, git push, bármilyen (szimulált) megbízás első leadása. Push csak kifejezett kérésre.
- Titok soha nem kerül a repóba vagy image-be; csak `.env.example`.
- Agent-container: non-root user, legkisebb jogosultság, egress allowlist, erőforrás- és költséglimitek.
- Pénzügy: alapértelmezés az IBKR paper számla; IBKR írási jog csak az Execution agenté.
- Verziókat (Agent SDK, A2A, OTel GenAI, broker API) webkereséssel ellenőrizd, és rögzítsd a döntési naplóban.

## Konvenciók
- Agent: `agents/<név>/` (kebab-case); skill: `agents/<név>/skills/<skill>/SKILL.md`.
- `libs/` = importált kód, `services/` = futó, nem-agent container.
- Állapot soha nem a container fájlrendszerében: Postgres (A2A task store, portfólió-tükör, tudásbázis, döntési napló).
