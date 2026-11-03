# OLC33 — Quando un vantaggio economico estremo è riconoscibile *ex ante*?

**Data:** 3 novembre 2026. **Decisione:** STOP (non promuovere un nuovo motore di selezione). 
**Protocollo bloccato prima di guardare gli esiti OLC33:** [GitHub commit `05b1d17`](https://github.com/AM1975MA/Test/commit/05b1d1735e2528e0f0512dbf029d1831057cce52).
**Dati di origine:** OLC32, commit [`3717924`](https://github.com/AM1975MA/Test/commit/3717924ef11e58263961d0c98a0b806976a3c8fb), con maschere e date corrette. Nessun intervento su `main`.

## Principale risultato

Sul campione principale gennaio 2021–dicembre 2024 (48 segnali per mercato), il classificatore P1 **non migliora** la baseline P0 della frequenza di eventi estremi né EU né USA. Sebbene vi siano singoli cambi ETF redditizi, questi non sono sufficienti a dimostrare potere predittivo riproducibile.

| Indicatore | EU | USA |
| --- | ---: | ---: |
| Mesi | 48 | 48 |
| Coppie Top1–Top(2..5) valutabili | 190 | 192 |
| Frequenza di vantaggio netto >= 300bp (tutte le coppie) | 20,00% | 17,71% |
| Brier P0 null (inferiore migliore) | 0,16615 | 0,15595 |
| Brier P1 classifier | 0,17682 | 0,17116 |
| Average Precision P1 | 0,19098 | 0,17903 |
| Mesi con switch secondo soglie fissate | **1** | **7** |
| Switch con vantaggio netto >= 300bp | 0 | 2 |
| Precisione eventi estremi per switch | 0,00% | 28,57% |
| Frequenza eventi estremi, challenger non scelti | 19,79% | 17,71% |
| Frequenza switch con perdita netta <= -300bp | 0/1 | 3/7 |
| Vantaggio medio rispetto ad AUTH Top1 su tutti i mesi (bp/mese) | **+3,754** | **−6,221** |
| Guadagno incrementale in somma log-bp rispetto a Top1 | +180,205 | −298,602 |

La media congiunta sui 96 mesi-mercato valutabili è **−1,233bp/mese**. Bootstrap descrittivo con 2000 campioni di blocchi contigui da 6 mesi, EU e USA accoppiati per *mese solare* (non per identica data di segnale): **intervallo 95% [−44,825; +44,211] bp/mese**. Non prova né l'assenza assoluta di un segnale né la sua presenza: l'intervallo è ampio, ma il protocollo ha un gate primario negativo.

## Metodologia preregistrata

- Per ogni mese e mercato, incumbent = rank1 di AUTH FUSION; candidati = rank2,3,4,5. Classificazione dell'evento `r_O2O(challenger)-r_O2O(leader)-20bp >= 300bp`.
- Feature = 10 differenze tra candidato/leader e 2 indicatori di contesto, tutti osservabili al segnale. Modello pooled EU/USA `StandardScaler+LogisticRegression(C=.1)`; 6 training annuali cronologici 2021–2026 con soli esiti maturi prima dell'anno. Soglie congiunte P1>=.40 e P1-P0>=.10; massimo un challenger per mese.
- P0 = incidenza storica pesata di eventi positivi osservabili nel solo training. Un label futuro non può entrare nel ranking o nell'attivazione dell'azione.
- 2025 e 2026 parziale NON usati per scegliere modello, soglia, target o promozione; i risultati negativi del 2021–2024 chiudono il test. Non è stato tentato altro tuning dopo il test.

## Gate preannunciati e valutazione

| Gate | Europa | USA | Decisione |
| --- | --- | --- | --- |
| Brier P1 < P0 | FALLITO | FALLITO | STOP |
| Precisione >= 1,5 × frequenza challenger non scelti, con >=12 switch | FALLITO (1 switch) | FALLITO (7 switch) | STOP |
| Rendimento incrementale medio positivo dopo costo ipotetico | PASSA | FALLITO | STOP |
| Tasso di grossi svantaggi non superiore ai challenger non scelti, con >=12 switch | FALLITO per numerosità | FALLITO per numerosità | STOP |
| Limite inferiore bootstrap congiunto > 0bp | — | — | FALLITO |

L'ipotesi operativa di trovare situazioni *ex ante* in cui un grande vantaggio economico sia sfruttabile in modo affidabile **non è supportata da questo test**. Non cambiamo gli iperparametri per cercare un vincitore retrospettivo.

## Esempi di segnale che spiegano la fragilità (solo diagnostici)

- USA segnale 2021-12-31: TUR → UNG, +2357bp netti; tuttavia USA 2021-10-29 KRE → PALL, −1614bp e 2021-06-30 TUR → TAN, −896bp. Un successo estremo non rende prevedibili i successi successivi.
- UE: unica azione 2021-02-26 IS3N.DE → EXX1.DE, +180bp netti, **sotto** il criterio evento >=300bp; quindi 0 eventi estremi correttamente catturati.

## Integrità dati e verifica indipendente

- Input frozen OLC32 SHA256 `83b5190501ba79029e1677d719a22893eaa98bddeb6042de2a46a885bca32d16`; archivio OLC32_RESULTS.zip SHA256 `aef33c5c1aac60a944f7cf767b7ee637eb4ca254710b431c95b5f13a67fd6b8d`.
- 720 coppie Top5 costruite; 712 hanno entrambi i label Open→Open utilizzabili nell'intero 2019–2026. La ricostruzione indipendente via merge ritorna differenza massima **0,0bp**.
- Durante la verifica, l'alterazione simulata degli outcome 2024 lascia **identiche** tutte le previsioni fino al 2024 (0 differenza); cambia invece 94 previsioni 2025, che dipendono lecitamente da training 2024 ormai maturo. Rerun previsioni con divergenza massima numerica <1e−16.
- Due confini EU 2020-06-01 riposizionati al **2020-06-02**; il terminale 2026-06-30 non genera label futuri; LEEU.DE 2024-05-02 non spacciato per prezzo osservato; maschera USA raw originale non disponibile.
- Il file `OLC32_EU_2020_CORRECTED_LABEL_PATCH.csv` salva le **296 righe rettificate o interessate** dei due segnali (148+148) e le date originali/corrette. Le **278 osservazioni recuperate** erano 139+139 nuove label valide; il resto era già valido. Non sostituisce il dataset completo né cambia i replay storici originali.

## Limiti

L'intero campione è già molto esplorato in OLC01–32: preregistrazione di una nuova prova evita il tuning su questi esiti specifici ma non crea un holdout completamente indipendente. USA non ha maschera originale di quotazioni osservate; mancano completa certificazione point-in-time, quotazioni bid-ask all'asta, spread, tasse, fx, ETF delistati e dividendi/total return. Costo 20bp per switch è un costo *ipotetico fisso* a fini diagnostici: i guadagni netti sono spread di log-rendimento Open→Open, non P&L operativo verificato.

## Per riprodurre

```bash
python olc33_tail_condition.py \
  --input OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz \
  --out results
python verify_olc33.py
```

Richiede Python, numpy, pandas, scikit-learn; input SHA256 obbligatorio. Risultati in `OLC33_RESULTS.json`, `OLC33_TRAIN_AUDIT.csv`, `OLC33_DECISIONS.csv`, `OLC33_MARKET_METRICS.csv`, `OLC33_OOF_PAIRS.csv.gz`, `OLC33_INDEPENDENT_VERIFICATION.json`, manifest. Non si prosegue al replay completo rischio/costi: gate fallito.
