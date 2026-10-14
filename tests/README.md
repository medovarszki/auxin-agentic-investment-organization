# tests/

- `e2e/`: végponttól végpontig futó füsttesztek *(8. fázis)*, köztük a szándékosan rossz esetek: gyenge ötlet (Research elutasítja), szabálysértő javaslat (Portfolio Manager visszadobja), már nem indokolt pozíció (review zárást javasol), lezárt döntés eredménye a tudásbázisba kerül.
- `fixtures/`: tesztadatok.

Az egységtesztek a komponensek mellett vannak (`agents/<név>/tests/`, `libs/<lib>/tests/`).
