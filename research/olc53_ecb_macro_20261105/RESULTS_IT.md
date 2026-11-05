# OLC53 — Informazione BCE aggiuntiva nel selettore OLC52 (5 novembre 2026)

**Esito: NO PROMOTION.** Manteniamo invariati OLC19 e OLC52. Questo è un esperimento retrospettivo in un periodo già esaminato numerose volte, non una conferma fuori campione.

## Fonte e feature

Sono stati trascritti dalla [tabella storica BCE sui tassi ufficiali](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html) 21 eventi di tasso sui depositi (2016–giugno2026), con data di efficacia. Per evitare anticipazioni, ciascun evento è disponibile al modello non prima di **sette giorni dopo l'entrata in vigore**. Le feature aggiuntive fissate prima dell'esito sono: livello %, variazione nei precedenti 90 giorni solari, giorni dall'ultima modifica (cap 180). EU/USA sono mantenuti come controlli separati.

Modello Ridge alpha20 con scaler train-only e minimo 18 etichette di rendimenti maturate; target: premio mensile netto della policy 25/75 vs 50/50. Si è verificata la parità della policy risk-only rispetto a OLC52 e del conto contabile baseline OLC19.

## Risultato europeo (CAGR, costo legacy 0,001)

| Metodo | 2021–2024 | FULL feb2019–lug2026 |
|---|---:|---:|
| OLC19 50/50 | 23,20% | 19,76% |
| Min-var 25/75 sempre | 29,31% | 20,84% |
| OLC52 Ridge tre feature rischio | **25,85%** | **21,05%** |
| OLC53 rischio + tre feature BCE | **24,15%** | **19,55%** |
| OLC53 rischio + solo livello BCE | 24,60% | 20,39% |

Ridge UE RMSE sul premio economico mensile 2021–24, 45 eventi appaiati: **141,99 bp OLC52** vs **169,29 bp OLC53**. Intervallo bootstrap descrittivo a blocchi di 6 mesi sul miglioramento della MSE [−25.206,+1.038] bp², contiene zero. Anche nel 2025–giugno2026 il RMSE peggiora lievemente (126,52→128,14). Con coefficiente costo 0,003 nel MAIN, OLC52 22,35% vs OLC53 20,67%.

La serie BCE è poco spiegata linearmente dalle tre feature OLC52 (R² <0,08 per ciascuna nel 2021–2024): nuova informazione **non implica** nuova predittività.

## QA e limitazioni

Controlli indipendenti verificati per EU e USA: effettività BCE sempre anteriore di almeno 7 giorni, train labels maturate prima dei segnali, nessun duplicato mercato/mese, baseline Ridge OLC52 identica e accounting del 50/50 OLC19 identico. Nessuna promozione del candidato.

I dati ECFIN sentiment sono stati identificati ma **non utilizzati**: non è stato possibile costruire un dataset verificato dei vintages effettivamente pubblicati; le serie oggi disseminate subiscono revisioni e destagionalizzazioni retroattive, quindi sostituirle ai vintages causerebbe possibile leakage. Le serie BCE di curva e aspettative non sono state acquisite in forma storicamente verificabile nel lotto.

Nel solo checkout GitHub non sono inclusi i binari OLC19/52 né i 23 file del bundle. Rapporto integrale, sorgenti Python, source CSV BCE, matrice delle decisioni, output mese per mese, controlli indipendenti, chart e SHA in ChatGPT Library: `/ETF_Research/OLC53_Macro_20261105/OLC53_VERIFICATO_20261105.zip`. Il codice è eseguibile ripristinando i checkpoint originali nel path dichiarato negli script.

**Successiva priorità:** ottenere curva forward/tassi di mercato e indicatori ECFIN point-in-time, non continuare a moltiplicare feature sui tassi ufficiali correnti.
