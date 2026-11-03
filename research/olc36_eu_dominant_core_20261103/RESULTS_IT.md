# OLC36 — EU: dominanti persistenti con core a isteresi

**Data:** 3 novembre 2026. **Esito:** STOP. **Ricerca EU-only; USA invariato.** Nessuna modifica a `main`, nessuna operazione, nessun adattamento dei parametri dopo aver visto gli esiti.

## Obiettivo e ipotesi

La richiesta era chiara: **far seguire meglio gli ETF europei che diventano dominanti**, ossia anticiparne l'inclusione e conservarli quando la leadership dura, anziché cercare il vincitore di ogni singolo mese. Il protocollo della regola DOM_CORE è stato pubblicato **prima del primo calcolo degli esiti**: [commit `6cc8790`](https://github.com/AM1975MA/Test/commit/6cc8790fec75154dc3a71f1e48e34b2744901166). I dati 2019–2026 sono stati già estesamente esplorati negli esperimenti precedenti: questa prova è **retrospettiva, esplorativa, NON un nuovo holdout indipendente**.

Sono stati preservati senza modifiche:

- **USA OLC17**, `TOP2_CONTEXT_REVALUE/ALL_PREOPEN_V6`, CAGR storico 2021–24 **52,3006%**, MaxDD **−19,7902%** (contratto di sensibilità informativa preopen);
- **USA OLC19**, `TOP2_CONTEXT_REVALUE/FAST_LOCK3`, costo legacy .001, CAGR storico **50,7722%**, MaxDD **−20,2260%** (contratto FAST_LOCK3);
- originale europeo AUTH FUSION (primi due ETF), modelli, dati, V6, rischio e trading.

## Regola realmente testata

Primo posto invariato: AUTH Top1. Il secondo può diventare un ETF **DOM_CORE** selezionato automaticamente e senza alcuna lista di ticker preferiti:

1. Rendimenti passati 126 e 252 sedute entrambi nel **decile migliore** del paniere UE;
2. Rendimento passato 63 sedute nel **quartile migliore** e 21 sedute superiore a −5%;
3. Condizione di top-decile a 126 sedute in almeno **2 degli ultimi 3 segnali**;
4. Conservazione del core finché rimane almeno nei **primi 20%** dei ritorni 126/252, positivo a 63 sedute e non perde oltre il 5% a 21 sedute.

Se non c'è un core valido, resta AUTH Top2. Se il core coincide con Top1, resta AUTH Top2 come secondo. Tutti i rank/filtri sono ricostruiti da sole feature con `source_date <= signal_date`. Il core è una **seconda posizione persistente**, non un bonus continuo al ranking come OLC25 né un correttore Ridge/KAMA come OLC26–30.

## Esito principale 2021–2024 (48 decisioni mensili Europa)

| Indicatore | AUTH Top2 | DOM_CORE |
|---|---:|---:|
| Mesi totali | 48 | 48 |
| Mesi con cambio effettivo della coppia | — | **41** |
| Mesi con core rilevato | — | **44** |
| Rendimento annuo composto del **proxy mensile** 50/50 | **27,93%** | 8,24% |
| Max drawdown del **proxy mensile** | **−18,13%** | −22,70% |
| Rateo delle posizioni nei migliori 10% sui sei mesi futuri | **26/96 = 27,08%** | 21/96 = 21,88% |
| Extra log-rendimento mensile netto (DOM − AUTH) | — | **−139,31 bp** |
| Intervallo bootstrap descrittivo 95% (6 mesi, 2000 campioni) | — | **[−248,76; −42,39] bp/mese** |

La somma delle differenze mensili è **−6686,98 log-bp** in 48 segnali. Entrambe le strategie hanno il medesimo prima posizione Top1. Il calcolo applica **20bp per unità di mezzo-turnover**, con ribilanciamento ogni mese, e confronta Open osservate iniziali/finali. **Non** simula V6, FAST_LOCK3, le protezioni intramensili o la reale formazione del prezzo di esecuzione. I 27,93% e 8,24% sono CAGR di un *proxy 50/50 mensile* e **non** sono confrontabili direttamente con il 23,20% di CAGR del motore EU OLC19 o con i 50,77% USA.

### Segno per anno

| Anno | Sostituzioni Top2 | Differenza media mensile netta DOM−AUTH (bp) |
|---|---:|---:|
| 2021 | 10 | −100,80 |
| 2022 | 10 | −137,92 |
| 2023 | 11 | −231,39 |
| 2024 | 10 | −87,13 |

Il peggioramento non è confinato a un singolo anno. Il costo non spiega il risultato: nel periodo DOM_CORE effettua meno turnover nominale della Top2 autentica (27 contro 33 unità annualizzabili di *half-turnover* aggregate sui 48 mesi), mentre la differenza media **lorda** dei rendimenti semplici è già **−147,51 bp/mese**.

### Il caso diagnostico QDVE.DE

Il benchmark QDVE.DE è stato scelto ex post nei vecchi studi; NON compare nella regola di selezione. Nel 2020 DOM_CORE lo seleziona in **7/12 mesi** mentre FUSION non lo include mai. Ma nel 2021 lo seleziona solo 2 volte, nel 2022 e 2023 mai, e nel 2024 **5 volte contro 6** di FUSION. Anticipare un campione noto **non** implica migliori decisioni nelle 48 finestre del test principale; non si seleziona retrospettivamente un'eccezione mirata a QDVE.

### Origine del fallimento

In 2021–2024 DOM_CORE individua sistematicamente ETF con momentum plurimensile recente, ma il rendimento del prossimo mese è mediamente inferiore a quello del secondo ETF scelto da FUSION. Diversi esempi di sostituzioni avverse si trovano nel CSV mensile: 2022-01 (EXV6.DE→XB4A.DE, −1051bp netti); 2023-02 (XS8R.DE→EXX1.DE, −890bp); 2023-04 (VVSM.DE→EXV9.DE, −852bp). Sono **episodi descrittivi**, non casi scelti per aggiustare soglie.

## Gate preregistrati

| Requisito | Esito |
|---|---|
| Almeno 12 modifiche del Top2 | PASSA (41) |
| Copertura ex-post delle coppie >=95% | PASSA (48/48) |
| Differenza netta mensile positiva | **FALLISCE** |
| Bootstrap 95% con limite inferiore >0 | **FALLISCE** |
| Top-decile futuro 6 mesi: +5 punti percentuali | **FALLISCE** (−5,21 pp) |
| MaxDD del proxy non peggiore di oltre 3 pp | **FALLISCE** (peggiora di 4,57 pp) |

**Decisione obbligata: STOP**, nessuna nuova soglia o ottimizzazione su questo stesso storico, nessuna integrazione dei segnali OLC36, nessun nuovo NAV OLC19/V6 finché i criteri fondamentali non sono raggiunti in un esperimento diverso e indipendentemente valido.

## Verifiche e limitazioni

- SHA256 dell'archivio OLC32 e del CSV corrected rispettati; 90 decisioni EU, 48 segnali nel periodo principale, nessun ticker duplicato, Top1 originale invariato;
- **0 uso di label futuri** nella funzione `select()`, che accetta solo input ex-ante; perturbare radicalmente gli outcome dopo 2023 non cambia alcuna decisione;
- controlli indipendenti di rank as-of e 83 stati `core` lungo tutti i segnali; ricalcolo contabile di **178 portafogli/mese valutabili**, massimo scarto **2,3×10⁻¹³ bp**;
- ricalcolo indipendente di **336 posizioni** nei target futuri a sei mesi, scarto massimo **9,1×10⁻¹³ bp**; intervallo bootstrap ricostruito esattamente;
- quotazioni EU 2020 corrette, missing `LEEU.DE` preservato, segnale terminale 2026-06 senza etichetta; nessun filtro di ammissibilità futura usato in fase decisionale;
- il target dei migliori ETF a sei mesi è **solo un'etichetta di valutazione**, non una scelta effettuabile prima dei rendimenti; le finestre a sei mesi si sovrappongono e non sono indipendenti;
- dati storici già ampiamente esaminati, possibili survivorship, assenza total-return, valori dei dividendi/FX, spread, slippage, quote point-in-time e meccaniche operative complete. Nessun guadagno certificato.

## Direzione di ricerca dopo OLC36

Il limite non sembra semplicemente la mancanza di un meccanismo per **tenere** un titolo forte. Il core resta spesso investito (44/48 mesi), eppure produce un peggior differenziale. Bisognerebbe riuscire a distinguere **forza che proseguirà** da **forza in esaurimento** mediante informazioni non ridondanti e nuove finestre prospettiche. Solo dopo una dimostrazione del beneficio sul prossimo periodo Open→Open avrebbe senso costruire un nuovo portfolio replay con V6, FAST_LOCK3 e costi realistici. Nessun intervento su USA.

## Artefatti

`src/run_olc36.py`, `src/verify_olc36.py`, `results/OLC36_EU_CORE_DECISIONS.csv`, `results/OLC36_MONTHLY_PROXY.csv`, `results/OLC36_FUTURE6_RETENTION_DIAGNOSTIC.csv`, `results/OLC36_EU_ASOF_RANKS.csv`, `results/OLC36_ANNUAL.csv`, `results/OLC36_QDVE_DIAGNOSTIC.csv`, `results/OLC36_BOOTSTRAP.csv`, `results/OLC36_SUMMARY.json`, `results/OLC36_INDEPENDENT_VERIFICATION.json`, `figures/`. Tutti gli output sono ricostruibili dal solo OLC32 frozen archive verificato via SHA.
