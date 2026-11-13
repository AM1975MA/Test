# OLC102 — Ricalcolo giornaliero dei veri rank ML e medie ponderate

**13 novembre 2026 · Revisione retrospettiva; nessuna promozione operativa.**

## 1. Conclusione

Sono state ricostruite le 125 feature Return e 42 feature Hybrid con le formule originali alle 90 chiusure mensili e alle successive una/due chiusure. Sono stati richiamati i modelli annuali ET/XGB, Return125 e OLC14 già addestrati e congelati; **nessun refit su outcome nuovi**. Per isolare le differenze nella popolazione dei percentili, i cambiamenti di score dei modelli dal giorno iniziale sono applicati agli score mensili canonici OLC19, senza alterare l'ordinamento storico al giorno di segnale.

Il test completo con V6 e FAST_LOCK3 comprende **76 replay nativi** (19 bracci × 2 mercati × 2 ipotesi di costi). **Nessuna delle medie ponderate testate supera il Top2 originale a timing identico in entrambi i mercati.** Il candidato di ricerca OLC67 rimane congelato e non viene sostituito.

## 2. Risultati economici comparabili

Per ogni media su tre chiusure il confronto valido è **FIXED_DAY2**, stesso ingresso alla terza apertura; cambiano solo i due ETF, non timing, V6 e protezione. Le formule dei pesi si riferiscono al rango percentile (non al rendimento):

`S_t = w0 * rank(ML_CLOSE0) + w1 * rank(ML_CLOSE1) + w2 * rank(ML_CLOSE2)`

L'azione è ammissibile soltanto all'apertura dopo la chiusura utilizzata. La politica `ML_SCORE_AVG` media invece direttamente gli score contestuali.

**FULL** dalla prima apertura febbraio 2019 all'apertura del 1º luglio 2026; CAGR annualizzato a 252 sedute secondo il motore OLC19, costi nominali legacy `fee=0.001`, `stop_friction=0.001`. Non sono prezzi/slippage di un broker certificato.

| Architettura | CAGR EU | CAGR USA | MaxDD EU | MaxDD USA |
|---|---:|---:|---:|---:|
| OLC19 originale · immediato / 50-50 | +19.76% | +39.48% | -28.61% | -26.12% |
| OLC67 · MINVAR63 / DELAY3 | +22.61% | +42.10% | -26.59% | -27.60% |
| OLC19 · 50-50 / DELAY3 nativo | +22.05% | +43.26% | -28.65% | -30.40% |
| Top2 originale · terza apertura / 50-50 | +22.19% | +42.81% | -28.65% | -30.40% |
| Top2 originale · terza apertura / MINVAR63 | +22.10% | +42.43% | -26.51% | -27.72% |
| ML della prima chiusura aggiuntiva / 50-50 | +15.25% | +26.87% | -33.43% | -26.65% |
| ML della seconda chiusura aggiuntiva / 50-50 | +18.16% | +13.42% | -38.44% | -36.09% |
| ML media 80/15/05 / 50-50 | +17.82% | +38.28% | -31.43% | -30.40% |
| ML media 50/30/20 / 50-50 | +16.17% | +33.53% | -36.04% | -30.68% |
| ML media 20/30/50 / 50-50 | +21.86% | +22.50% | -30.29% | -33.66% |
| Media degli score 50/30/20 / 50-50 | +15.77% | +28.38% | -35.93% | -30.68% |
| ML media 80/15/05 / MINVAR63 | +17.59% | +36.33% | -28.14% | -27.72% |
| ML media 50/30/20 / MINVAR63 | +15.60% | +27.34% | -33.63% | -28.58% |
| ML media 20/30/50 / MINVAR63 | +20.81% | +17.51% | -28.78% | -32.76% |

La media **50/30/20** con pesi 50/50 scende da **22,19% a 16,17% EU** e da **42,81% a 33,53% USA** contro FIXED_DAY2 (−6,02 e −9,28 punti CAGR). Il drawdown UE peggiora da −28,65% a −36,04%. Il peso MINVAR63 non salva la media: 15,60% EU e 27,34% USA.

La media **80/15/05** è più conservativa ma non domina: 17,82% EU e 38,28% USA contro lo stesso Top2 congelato con timing fisso. La media **20/30/50**, più sensibile agli ultimi ranghi, recupera quasi la baseline in EU (21,86%), ma perde molto in USA (22,50%). Non è lecito scegliere per mercato il peso vincitore ex post.

![OLC102 NAV Europea](results/OLC102_NAV_EU.png)
![OLC102 NAV USA](results/OLC102_NAV_USA.png)

## 3. Qual è la frequenza di cambiamento dei Top2?

I rank giornalieri effettivi comportano rotazioni rilevanti anche quando il modello originale è invariato:

| Politica | EU Top2 diversi | USA Top2 diversi |
|---|---:|---:|
| ML_DAY1 | 66/90 | 63/90 |
| ML_DAY2 | 70/90 | 68/90 |
| ML_AVG_80_15_05 | 17/90 | 14/90 |
| ML_AVG_50_30_20 | 43/90 | 40/90 |
| ML_AVG_20_30_50 | 55/90 | 58/90 |
| ML_SCORE_AVG_50_30_20 | 43/90 | 46/90 |

L'80/15/05 limita i cambi a 17/90 UE e 14/90 USA, ma non produce un miglioramento economico. Il problema quindi non è soltanto il numero di sostituzioni: conta la qualità dei cambiamenti e il loro percorso di rischio. Il riordino giornaliero può penalizzare la selezione mensile originale senza che la stabilità visiva del ranking ne evidenzi immediatamente il costo.

## 4. Incremento al medesimo timing e incertezza

Intervalli **descrittivi** al 95% su differenza di **log-rendimento annualizzato** (non differenza di CAGR), 5000 bootstrap circolari appaiati a blocchi di sei mesi, seed 102113. Lo storico è stato ripetutamente studiato da OLC01–102; non sono corretti per selezione/multipli test. I due mercati non sono prove indipendenti.

| Contrasto rispetto al Top2 originale alla terza apertura | Δ log annuo EU in pp [IC95%] | Δ log annuo USA in pp [IC95%] |
|---|---:|---:|
| ML media 50/30/20 / 50-50 | -5.05 [-10.26; +0.09] | -6.72 [-16.81; +3.49] |
| ML media 80/15/05 / 50-50 | -3.63 [-7.28; -0.43] | -3.22 [-7.71; +0.69] |
| ML media 20/30/50 / 50-50 | -0.27 [-8.34; +8.08] | -15.34 [-26.12; -2.98] |
| ML media 50/30/20 / MINVAR63 | -5.47 [-11.76; +0.36] | -11.20 [-22.04; -0.86] |

La media 50/30/20 perde economicamente nel campione, ma i rispettivi intervalli per la differenza 50/50 includono un valore molto vicino allo zero (EU) e zero (USA): i risultati non possono essere interpretati come probabilità calibrata di fallimento futuro. Alcune varianti conservative o MINVAR mostrano intervalli con esclusione dello zero su uno dei mercati, ma si tratta di analisi post-ricerca.

## 5. Stress costi

Stesso contratto, con coefficienti legacy `fee=0.003`, `stop_friction=0.005`; non sono spread broker osservati.

| Architettura | CAGR EU | CAGR USA |
|---|---:|---:|
| OLC19 originale · immediato / 50-50 | +15.37% | +28.65% |
| OLC67 · MINVAR63 / DELAY3 | +18.00% | +31.43% |
| Top2 originale · terza apertura / 50-50 | +17.69% | +31.59% |
| ML media 80/15/05 / 50-50 | +13.26% | +27.26% |
| ML media 50/30/20 / 50-50 | +11.46% | +22.98% |
| ML media 50/30/20 / MINVAR63 | +10.78% | +17.61% |

Le nuove medie non recuperano il divario nel test di costo più elevato. Il turnover, gli stop, il dettaglio annuale e tutti gli scenari sono nelle scorecard e nei log giornalieri.

## 6. Validazione tecnica indipendente

- 90 decisioni mensili per mercato. Alla chiusura originale, **125/125 feature Return e 42/42 Hybrid** coincidevano con il pannello congelato. L'appartenenza ai cluster resta quella mensile, non viene ricalcolata usando dati successivi.
- USA: rank Return125 originale identico per 90/90 mesi e punteggi fino a precisione macchina. UE: per ottenere 90/90 classifiche identiche è necessario il checkpoint annuale **RSI_DOMAIN**; il raw percentile può differire fino a 0,0400 perché la popolazione di normalizzazione originale non coincide esattamente con il sottoinsieme eleggibile del test. Si utilizzano quindi soltanto **variazioni giornaliere** applicate agli score canonici originali.
- ET e cinque teste OLC14 riaperte dal modello: predizioni grezze ET allineate a precisione macchina; XGBoost tolleranza massima osservata circa 7,15×10⁻⁸. Alcuni percentili presentano differenze su pareggi contigui dell'ordine di 0,00134. Non vengono dichiarati bitwise i rank dei giorni successivi.
- Stadio contestuale OLC19: **90/90 Top2 storici esatti**, errore massimo negli score originali ~2,58×10⁻¹⁴ UE / 1,81×10⁻¹⁴ USA.
- Motore OLC19: parità **bitwise 7/7 matrici** delle baseline in entrambi i mercati; corrispondenza di `alt` V6; tutti i 76 CAGR e MaxDD verificati indipendentemente con convenzione temporale originale.
- L'ultima decisione del 30 giugno 2026 non dispone nel checkpoint delle due chiusure future: in quel caso resta il Top2 originale, senza inventare una previsione.

## 7. Limiti e decisione

La strategia originale è **mensile**. Qui applichiamo gli stessi learner annuali alle due chiusure successive, tenendo fissi eleggibilità, cluster e modelli; è un'**estensione sperimentale giornaliera**, non una versione quotidiana già in uso e certificata del modello originale. L'aggancio agli score mensili serve a rispettare esattamente la baseline, ma non dimostra capacità fuori campione o esecuzione broker.

Restano i limiti generali: universo point-in-time parziale, missing quote USA, adjusted versus total return, spread reali, slippage di stop/gap ed esecuzioni nello stesso giorno. Il FULL 2019–luglio 2026 non è un campione vergine. Le ottimizzazioni a posteriori dei pesi sarebbero ulteriore overfitting.

**Decisione: non promuovere alcuna media dei veri ranking ML quotidiani.** Conservare OLC19 come baseline e OLC67 come candidato prospettico. La direzione più rigorosa non è esplorare altre percentuali sullo stesso storico, ma congelare eventualmente una regola di conferma con criteri economici verificabili e misurarla *prima* dei risultati futuri.

## 8. Riproducibilità

Sorgenti di lavoro: `build_daily_features.py`, `score_daily_models.py`, `compose_daily_rank.py`, `sim_backend.py`, `run_native_daily_rank.py`, `analyze_olc102.py`, `make_report.py`; riferimento OLC19 originale e checkpoint annui OLC07/08/11/14 separati.

Output: `OLC102_SCORECARD.csv`, `OLC102_SELECTION_CHANGES.csv`, `OLC102_PAIRED_BLOCK6.csv`, `OLC102_ANNUAL_RETURNS.csv`, `OLC102_DAILY.csv.gz`, `OLC102_*_QA.json`, grafici NAV. Per riproduzione esatta servono i checkpoint originali identificati nel manifest; non vengono ridistribuiti nell'archivio sperimentale.
