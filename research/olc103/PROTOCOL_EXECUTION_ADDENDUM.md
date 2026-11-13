# OLC103 — Addendum di esecuzione del cap (prima dei risultati economici validi)

Il primo smoke-run dopo la preregistrazione ha identificato un errore di interfaccia della policy: `q['gross']` rappresenta uno stato informativo V6, ma l'effettivo limite del budget investito del motore OLC19 e' letto da `q['g']` (vedere `vector_engine.py`: `g=float(q['g'][k])`; `f=min(basef,g)`). La prima implementazione riduceva `q['gross']` e pertanto non riduceva l'esposizione reale; quei replay sono **inutilizzabili per un'affermazione economica**.

Senza cambiare soglie, date, classificazioni di stabilita', mercati, costi o set di strategie predefiniti, la riduzione economica viene ora eseguita su `q['g'][k+2:next_event] = min(q['g'], cap)`. `q['gross']` e il calcolo del candidato alternativo V6 non vengono alterati. L'overlay agisce esclusivamente alla terza apertura e successivamente; la coppia OLC19 resta invariata. I controlli ALL75 e ALL50 hanno **lo stesso cap effettivo** applicato in ogni mese. Non scegliere a posteriori policy vincitrici per mercato o periodo.

L'addendum viene scritto **dopo aver osservato il segnale predittivo di OLC103**, ma prima di misurare le performance economiche dei cap effettivi; non e' validazione indipendente ne' una preregistrazione blind.
