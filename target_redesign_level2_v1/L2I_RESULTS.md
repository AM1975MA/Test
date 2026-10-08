# L2-I — Distribuzione XGBoost e consenso tra modelli (8 ottobre 2026)

**STATO:** COMPLETATO, QA INDIPENDENTE PASS, **NO GO** per la robustezza, NESSUNA PROMOZIONE. Modificato soltanto `AM1975MA/Test`, branch `research/target-redesign-level2-v1`; `Etf_trader` invariato. [Protocollo preregistrato](L2I_PREREGISTRATION.md) al commit `dc1f4857f53686efdd8b6de57c46d71c636feb69`, antecedente alla lettura delle metriche.

## Fonti e cosa è stato realmente fatto

Abbiamo riusato — **senza nuovi fit** — i **tre modelli XGB canonici, uno per ciascuna vintage Yahoo**, ognuno già un ensemble di tre seed e fittato annualmente in modo causale nel lavoro L2-D. Li abbiamo interrogati sulle **medesime feature di inferenza Repeat2**, quindi il confronto non risente di input live differenti. Le tre acquisizioni Yahoo erano tutte scaricate nel 2026, anche per la storia 2017–2026: **non rappresentano gli snapshot point-in-time disponibili nel 2017**. Le tre vintage sono lo stesso mercato e non costituiscono tre holdout indipendenti.

Dati: frozen Original149, 149 ETF × **113 date mensili** febbraio 2017–giugno 2026 = **16.837** osservazioni uniche mature a 21 sedute. Tre score XGB per riga (50.511 score fonte) + Ridge comune Repeat2. La baseline XGB Repeat2 comune = XGB Repeat2 native (max differenza 0); Ridge Repeat2 comune = Ridge Repeat2 native (max differenza 0). Ogni ETF selezionato scambiato nel replay al prossimo Open storico rettificato, con fee 0,1% per lato; nessun filtro di disponibilità BIL come benchmark (BIL rimane normale ETF dell'universo).

**I due candidati fissi**:
1. `COMMITTEE_MEAN3`: media aritmetica dei **percentili di ranking** prodotti dai tre XGB su ogni data; nessun peso ottimizzato.
2. `COMMITTEE_TOP5_VOTE2`: considera soltanto ticker Top 5 in **almeno 2 di 3 modelli**, poi seleziona il migliore per punteggio medio, fallback Ridge se nessun consenso. Il fallback non è stato necessario in **0/113 date**; il vincolo cambia l'ETF in appena **1/113 date** rispetto a MEAN3.

## Qualità Top1 — stesso pannello input Repeat2

| Modello | NDCG@5 | Rank IC | Realized Top5 hit | Top1 realized net return 21 sedute | Exact winner |
|---|---:|---:|---:|---:|---:|
| XGB Repeat2 | 0,551665 | 0,070172 | 19,469% | +2,2480% | **7,965%** |
| Ridge Repeat2 | **0,562014** | **0,092881** | 7,965% | +1,7620% | 5,310% |
| **COMMITTEE_MEAN3** | 0,555398 | 0,065227 | **21,239%** | **+2,6980%** | 6,195% |
| **COMMITTEE_TOP5_VOTE2** | 0,555398* | 0,065227* | **21,239%** | **+2,7196%** | 6,195% |

\* NDCG e Rank IC per la regola Vote2 sono riportati rispetto al punteggio globale Mean3 **sottostante**, non all'ordinamento ristretto ai voti. Le sue metriche operative principali sono le selezioni Top1.

Il consenso non migliora la qualità del ranking globale su Ridge. Migliora lievemente la frequenza dei Top 5 e il rendimento realizzato medio rispetto a XGB Repeat2, ma **senza significatività statistica** in questo confronto storico.

## Verifica genuina del consenso — escludere un modello per volta

La stabilità di un'uscita Full3 rispetto a sé stessa sarebbe tautologica. È stato quindi calcolato `leave-one-vintage-out` (LOVO) a 2 modelli su **identico input Repeat2**:

| Coppia di esclusioni | Top1 agreement | Mean percentile Rank-MAD | Top5 overlap |
|---|---:|---:|---:|
| lascia fuori repeat1 vs repeat2 | **68,14%** | **0,02830** | 80,53% |
| lascia fuori repeat1 vs repeat3 | **69,91%** | **0,02808** | 80,18% |
| lascia fuori repeat2 vs repeat3 | **65,49%** | **0,02844** | 82,65% |

Inoltre ogni LOVO due-modelli condivide un modello con gli altri: l'apparente accordo è **in parte meccanico** e non equivale a testare train indipendenti su dati futuri. Nelle tre esclusioni la frequenza Top5 dei LOVO Mean oscilla **17,70–20,35%**, rendimento 21d scelto **+2,35–2,55%**.

Gate fissato prima di osservare gli esiti: ogni coppia Top1 agreement >=90%; Rank-MAD <0,01; realized Top5 hit >=15%; realized Top1 net return >= Ridge. **Entrambi i candidati superano i due gate di qualità, ma falliscono entrambi i gate di stabilità**. Formalmente, **NO GO**.

## Verifica economica (solo Top1, non Hybrid24)

Replay unicamente sul pannello **Repeat2**, 112 mesi non sovrapposti, 2017–2026; fee 0,1% per acquisto e per vendita effettivi, senza trade fittizio all'ultima data. Non include la strategia canonica Hybrid24 (MA3, più componenti, basket/risk governor) e trascura slippage, tasse, liquidation gap e intramonth DD.

| Modello | CAGR proxy | Max DD su **soli saldi mensili** | Numero switch |
|---|---:|---:|---:|
| XGB Repeat2 | **22,17%** | −41,88% | 103 |
| Ridge Repeat2 | 17,15% | **−31,66%** | 94 |
| Committee Mean3 | **29,55%** | **−50,23%** | 97 |
| Committee Vote2 | **29,32%** | **−50,23%** | 98 |

**Avviso rischio:** il +29,55% è un proxy di CAGR *sullo storico già usato* e non prova un vantaggio prospettico. Il DD di −50,23% è *peggiore* sia di Ridge sia di XGB Repeat2. In 2020 la media delle scelte a 21 giorni è **−4,45%** per Committee Mean3 contro **+3,56%** Ridge; forte dipendenza dal regime e concentrazione di perdite. La metrica DD osservata solo alle scadenze mensili può sottostimare il rischio intramensile.

## Inferenza paired (block bootstrap 3 mesi, 10.000 repliche)

95% intervalli descrittivi **non corretti per multipli test**, non conferma di generalizzazione. Committee Mean3 meno XGB Repeat2:
- Rendimento medio 21d per scelta: **+0,004500** (+0,4500 punti percentuali), IC **[−0,006414, +0,017490]**; attraversa zero.
- Top5 hit: **+0,017699**, IC **[−0,035398,+0,070796]**; attraversa zero.
- Differenza log-return mensile netta nel proxy: **+0,004889**, IC **[−0,005129,+0,017922]**; attraversa zero.

Committee Mean3 meno Ridge Repeat2: rendimento medio 21d **+0,009360**, IC **[−0,009842,+0,029266]**; attraversa zero. I risultati storici sono sottoposti a ripetuta esplorazione.

## Audit indipendente e riproducibilità

Audit indipendente **PASS**: random 24 date ricostruite con `scipy.stats.rankdata` e selezione dei ticker senza riusare le funzioni principali; tutti e quattro i ledger di esecuzione riconciliati con costi effettivi, apertura successiva, wealth, 112 periodi, nessun trade terminale fittizio; gli score Repeat2 common e native per XGB e Ridge sono esattamente uguali; chiavi complete e senza duplicati.

SHA256 input:
- XGB common: `15a3c36c2f002ad68fb675b9bbf5afeb19f5ecc833270844abcd5429596d7417`.
- XGB native: `c292ced435f6b75d4a3e00dd272c85f77521bb78350bff5d68753776a8047b76`.
- Ridge common: `163a75d8e6a08640284fd879dec3a1d748a4f1d156a68bcf66f91c775dcb0849`.
- Ridge native: `e921bfd5e441e738a875e62d9487160a4e03e933e0bfce1ab311c43af68933f0`.

Script integrale eseguito `l2i_consensus.py` SHA256 `cb8ad075921fe2f973057badb1bdf3d2a788881aff126ae565edcb982ec9e71c` e outputs (SOURCE_SCORE_PANEL, rankings, decisions, LOVO, metrics, ledger, bootstrap, annual e audit) nel file ZIP consegnato in conversazione `ETF_Trader_L2I_consensus.zip`. **20 elementi, ZIP self-test PASS.** Dati originali Yahoo reperibili come artefatto GitHub Actions 11272972639, non duplicati nel repository.

## Verdetto / next research

La media dei modelli **recupera Top5 opportunity skill**, ma *non stabilizza a sufficienza i fit nonlinear XGB*: basta rimuovere una delle tre stime per cambiare ~30–35% delle scelte. Inoltre le code di perdita/DD peggiorano in questo semplice replay. **Non promuovere** e non modificare retroattivamente pesi o soglie per far passare il gate.

Il prossimo studio serio dovrebbe rimuovere la dipendenza da versioni di Yahoo tutte scaricate nel 2026 e impiegare vere **vintage point-in-time**, una distribuzione di retraining **bootstrap di blocchi temporali con perturbazioni identiche condivise e verificabili**, oppure post-2026 prospectively timestamped snapshots. Stabilità da stress truly independently sampled, risk-tail constraints e un holdout davvero nuovo sono condizioni indispensabili per uno switch verso Hybrid24.
