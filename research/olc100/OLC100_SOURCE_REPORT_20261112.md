# OLC100 — Verifica acquisizione prospettica / dati al 12 novembre 2026

**Stato: download completo, quote NON certificate per replay, nuovo segnale OLC19 NON generato.**

## Misure riproducibili
- Run: https://github.com/AM1975MA/Test/actions/runs/43313096224 (commit `f838a00245b984a42164b3c7a2a1d2fcb2416119`); audit indipendente: https://github.com/AM1975MA/Test/actions/runs/43312770318.
- Fonte: stessi universi congelati OLC19, **165 EU e 149 USA**, hash checkpoint `3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540`.
- **314/314 ETF scaricati**, **29,845 barre dal 2 luglio al 12 novembre 2026**: EU 15,839; USA 14,006. Singola serie `18MN.DE` con 95 sedute anziché 96 nel panel EU; non sono state riempite automaticamente.
- Controllo dei file: **316/316 SHA256 corretti**, nessuna modifica ai dati storici di raccordo OLC19.
- Raccordo prezzi (max errore relativo sui giorni comuni, dopo una sola riscalatura dichiarata): EU 0.155601%; USA 0.000025%. La scala è documentata, non costituisce una verifica di spread/prezzi eseguibili.

## Quote problematiche: non nasconderle
- **EU:** 7 ticker, **75 barre** con Low superiore a Open/Close o High inferiore a Open/Close. Ticker: BEL.BR, EM1015.MI, IMIB.MI, ISFA.AS, LYXIB.MC, TELE.PA, UTI.MI.
- **USA:** 8 ticker, **8 barre**, tutte con ultima anomalia il **12 novembre**. Ticker: CORN, DGS, EPP, EWD, EWI, RWO, RWX, USL.
- In totale **83 barre segnalate**. I valori grezzi non vengono corretti o eliminati; i flag sono conservati nella serie. I casi sono riproducibili anche con `Ticker.history` e quindi non semplici ticker assenti. Le anomalie USA dell'ultima seduta potrebbero essere provvisorie: va ripetuta la verifica su un nuovo snapshot, non presunto il dato corretto.

## Perché non esiste ancora un segnale Top2 verificato
Lo snapshot OLC19 contiene score originali solo fino al segnale del **30 giugno 2026** (apertura 1 luglio) e replay di conto fino al 1 luglio. Senza una riproduzione *bitwise* o strettamente certificata dell'upstream **Return125 + ET/XGB + memoria + FUSION + contextual revalue** non è lecito calcolare il Top2 di novembre riciclando un altro modello. Manca inoltre la prosecuzione legittima dello stato contabile **V6/FAST_LOCK3** in presenza delle nuove decisioni. Gli input raw Yahoo e i modelli V3 non sono sostituti equivalenti.

I prezzi 2 luglio–12 novembre 2026 sono raccolti **retrospettivamente** e non sono un holdout prospettico. La GitHub Action fallisce deliberatamente il gate `SOURCE_QA_PASS` per le barre sospette, non per un errore d'esecuzione del codice.

## Gate successivi (senza reottimizzazione)
1. Convalidare o correggere con fonti verificabili le 83 barre, preservando raw, revisioni e timestamp; certificare i calendari per mercato.
2. Ricostruire lo scorer originale su input 2026, dimostrare parità dei 180 eventi EU/USA storici e previsioni autenticamente as-of sulle date nuove; riprodurre il ledger OLC19 con rischio/cash/locks.
3. Solo dopo i due PASS, firmare prima della prima apertura utile il segnale nuovo, i pesi dei sei bracci congelati e gli input. Nessuna operazione live.

Il controllo automatico del **30 novembre 2026 alle 22:30 Europe/Rome** è stato pianificato per ripetere il gate dopo la chiusura dei mercati. Se i modelli o i dati restano incompleti, l'output sarà **BLOCCATO**, non un CAGR o un falso Top2.
