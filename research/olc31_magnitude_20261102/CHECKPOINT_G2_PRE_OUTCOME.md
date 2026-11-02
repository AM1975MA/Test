# OLC31 — G2: calibrazione cronologica preregistrata prima di stimare

2 novembre 2026. Il protocollo maestro è già fissato al commit `ce7b992e4ac175c3ca12c408ae842a3b74888b48`. G0: 32 portafogli parent identici; il prezzo Open 2020-06-01 manca per molti ETF europei. G1: nessuna raw feature domina in modo chiaro il FUSION in EU e USA (intervalli bootstrap ampi e ripetuti test esplorativi). **G2 non è una promozione basata su G1: è il confronto rigoroso, a bassa complessità, per respingere o sostenere l'ipotesi di informazione incrementale della magnitudine.** Nessun outcome G2 è stato letto quando sono state fissate queste regole.

## Contratti esatti
- EU165 / USA149; 2019–2026 come storico, 2021–2024 come finestra principale, gli altri anni sono diagnostici già esplorati.
- Target `ABS_BP = 10000*log(Open_e1/Open_e0)` e `REL_BP = ABS_BP - median(ABS_BP nello stesso mercato e signal_date su ticker con entrambe le aperture realmente disponibili)`. La mediana futura è solo un'etichetta di training/evaluation; non una feature.
- Granularità: una riga per `(market,signal_date,ticker)` con `entry_date` e `exit_date` effettivamente differenti e future; label mature se **exit_date STRICTLY < YYYY-01-01**.
- Righe EU con `observed=False` a entrata o uscita non hanno etichetta. USA quote preparate positive/finite, con caveat maschera originale assente. Tutti i mesi con <95% dei forecast ticker dotati di etichetta Open valida sono esclusi dal **training** (2020-04-30, 2020-05-29 in EU), e dal calcolo della mediana; vengono mantenuti nella tabella qualità. Questo è un contratto di qualità individuato in G0 e fissato **prima degli esiti G2**, non una selezione di mesi in base ai rendimenti.
- Le feature originali sono `FUSION`, `RETURN_RAW`, `ET_RAW`, `XGB_RAW`, `C21_ET`, `C21_XGB`, `C42_ET`, `C42_XGB`, `C63_ET`, `C63_XGB`, tutti disponibili al signal Close. Non usare `fwd_ret_21`/TARGET, né classi settoriali future o identità ticker.

## Modelli, identico training cohort
- `B1`: Ridge alpha=10 su `FUSION` soltanto; 
- `B2`: Ridge alpha=10 su `FUSION` + tutti e nove i raw-score dichiarati (l'appartenenza al medesimo learner è preservata come nome feature). Nessuna scelta delle 2–3 feature migliori dopo G1.
- `B0`: baseline training-only della mediana per target, senza forecast. B0 è un controllo di livello economico, non un candidato di trading.
- StandardScaler per le feature fit solo sul training di ogni anno, con `sample_weight`; Ridge fit `sample_weight`; quattro fit indipendenti/anno (B1/B2 × ABS/REL). Stesso algoritmo/alpha/scale EU+USA; il train pesa **50% EU e 50% USA**, uguale peso per mese entro mercato e per ETF entro mese. Normalizzare `sample_weight` a media 1, senza privilegiare universi più grandi.
- Tutti i modelli usano **l'intersezione delle righe con tutte le dieci feature finite**, sia training sia evaluation: nessuna variante beneficia di più ticker o date; supporto di previsione senza label futura resta eleggibile a future decisioni (qui valutiamo solo file storici maturi). Nessun fitting delle previsioni BASE ETF.
- Fit expanding per year 2021..2026; solo righe con label exit prima del 1 gennaio dell'anno. Se <12 mesi eleggibili per mercato, fallback e audit esplicito senza fitting. La validazione è annuale prequential, nessun random split, nessuna scelta di alfa o modello in base al rendimento.

## Metriche e verifiche
- Primaria: differenza fra perdita MSE monthly-equalized `B1 - B2` su `REL_BP`, riportata separatamente EU e USA; positiva significa che B2 è più preciso. Accanto: differenza MAE, bias/intercetta/slope e IC95% bootstrap *descrittivo* a blocchi6 di 4000 estrazioni con seed20261102; non trattare zero come veto meccanico.
- Secondarie: qualità ABS_BP, per-mese Top2/Top5, signed pairwise spread Top1-Top2, rischio di outlier, costo opportunità solo proxy lordo e previsioni su Top20. Non usare CAGR, QDVE o rendimento netto per scegliere B1/B2.
- Controlli: 100% train label maturity, trasformazioni scaler intra-train, row-matching perfetto tra B1 e B2, market/month weights, causal prefix perturbation (mutare solo label dopo un cutoff e controllare predizioni precedenti), invariabilità a riordino delle righe, score non confusi fra ET/XGB, fallback e NaN espliciti. Se risultati ambigui, non avviare B3 o G4.
- In caso di un miglioramento comune apparentemente significativo, sono previsti cinque controlli negativi di training-only raw shuffle e un audit indipendente: NON li si sceglie per rendimento. Nessuna promozione senza G3/G4 e prospettiva futura.
