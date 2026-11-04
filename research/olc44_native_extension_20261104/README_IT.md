# OLC44 native extension — resoconto al 4 novembre 2026

**Stato: contratto sperimentale verificato; training nativo non ancora eseguito.** La strategia operativa resta invariata. Non attribuire un nuovo CAGR a questo lavoro.

## Universi congelati

| Braccio | Numero ETF | Confronto |
|---|---:|---|
| EU165_ORIGINAL | 165 | controllo originale |
| EU152_DEDUP_RESEARCH | 152 | deduplicazione OLC42 |
| EU165_PLUS4 | 169 | aggiunta ETF senza dedup |
| EU152_PLUS4 | 156 | dedup + aggiunta |
| USA149_ORIGINAL | 149 | controllo originale |
| USA149_PLUS3 | 152 | aggiunta ETF USA |

Le 13 coppie Acc/Dist sono **candidati research-only, non equivalenze storiche PIT certificate**. I nuovi ETF EU sono G2X.DE, USPY.DE, WTIC.DE, 2B76.DE. I nuovi ETF USA sono BOTZ, LIT, PAVE. Il roster e le firme degli input originali sono nei CSV/JSON di questa cartella.

## Ragione tecnica

OLC19 usa l'intera catena: primi score OLC11/14, re-ranking contestuale OLC16, alternativa V6 OLC17, gestione stop/LOCK3 OLC19. Aggiungere ETF modifica i percentili cross-sectional e può cambiare i target degli ETF precedenti. Il modello ampliato va quindi riaddestrato e rivalutato integralmente. Non basta appendere nuovi score.

I test presenti verificano: eleggibilità as-of, assenza di duplicati, maturità per intero mese dei label 63d e invarianti anti-leakage. La parità degli score originali si verifica su universo identico; non va richiesta dopo aver cambiato il training.

## Input binari e ripristino

I modelli originali sono nella Library, non nel checkout GitHub: OLC14 Heads 364165692 byte (SHA256 a8f2c1770dfdd329676293788180b96a92f79a598d1394a0aaaeb5d91346e458), OLC14 Results 40006829 byte (SHA256 4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1). Servono anche lo stato OLC16/17 e il checkpoint esecutivo OLC19. Lo script restore_original_olc14.py verifica hash e integrità prima di leggere modelli.

La sequenza necessaria per un vero confronto economico è: ripristino sorgenti e modello baseline, rigenerazione 42 feature per vecchi e nuovi ETF, target relativi maturati, refit annuale, contestualizzazione OLC16, V6 OLC17, esecuzione OLC19, metriche e confronto appaiato. I dati 2019–2026 sono già stati più volte esplorati; non sono un holdout vergine.

**Riferimenti 2021–2024 tuttora invariati:** OLC19 EU165 CAGR 23,1999%; USA149 CAGR 50,7722%. Nessun nuovo CAGR nativo convalidato in questo checkpoint.

Risultati di questo step: results/OLC44N_ARMS.csv, results/OLC44N_ARM_MEMBERSHIP.csv, results/OLC44N_CONTRACT.json, results/OLC44N_FULLSTACK_DEPENDENCIES.csv, results/OLC44N_FULLSTACK_READINESS.json.
