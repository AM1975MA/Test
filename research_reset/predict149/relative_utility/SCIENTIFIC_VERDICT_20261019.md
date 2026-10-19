# T149-J — Previsione del vantaggio economico fra i portafogli F3 e H1: risultati completi
19 ottobre 2026 | branch `research/149-relative-expert-utility-20261019`

## Decisione
**Nessuno dei tre nuovi meta-modelli supera i criteri predittivi e finanziari precongelati.** Il 50/50 F3/H1 mantiene il profilo di rischio più convincente sul vecchio corpus; J2 incrementa lievemente CAGR/Sharpe ma fallisce la correttezza delle sue previsioni e manca evidenza statistica di extra-rendimento. Tutti i risultati sono solo **retrospettivi**: il paniere dei 149 ETF USA è selezionato ex post, senza membership point-in-time, ha 64 ancore 2021–26 usate molte volte in altre prove, non dispone di validazione nuova né di esecuzione garantita su mercati italiani.

GitHub Action riuscita: https://github.com/AM1975MA/Test/actions/runs/39263599730
Protocollo congelato **prima** del test: `research_reset/predict149/relative_utility/PREREGISTERED.md`. Source `run.py`, test `test_run.py`; archivio completo numerico `results/{RESULT.json,FROZEN_64_ASOF_EXPERT_RELATIVE_FEATURES_PROB_AND_DECISIONS.csv,COSTED_DAILY_PORTFOLIOS_AND_KNOWN_CONTROLS.csv,SHA256_MANIFEST.txt}`.

## Dati fissi e strategia di valutazione
- Universi esattamente 149 ETF; modelli **F3, H1, H3 già congelati**, punteggi 9536 ETF×periodo, reali 1345 punti di apertura, 64 rinnovi ogni 21 sedute Feb 2021–Jun 2026.
- 10 feature **as-of** relative ai panieri correnti, non solo al mercato generico: margine standardizzato con cui F3 preferisce le proprie top5 rispetto alle top5 H1; specularmente H1; confronto dei margini, momentum differenziale 63d dei due panieri, rapporto volatilità 63d, correlazione 63d, distanza dei 10 beta fattoriali as-of, differenza di intervallo dei quantili residui già predetti, USO63−QQQ63, SPY vol21/vol63.
- Target `Y=log(wealth_F3_end / wealth_F3_start)−log(wealth_H1_end / wealth_H1_start)` per **solo il blocco completamente maturo**. Alla decisione del mese k è utilizzabile **al massimo il risultato k−2**, perché il risultato k−1 diventa disponibile all'Open del mese k (dopo il segnale alla Close precedente). Questo embargo è testato mediante modifica dei rendimenti futuri. Baseline prior storico solo sui periodi completamente maturati.
- J1 regola fissa margini di confidenza punteggi normalizzati, sposta a F3 75%/H1 25% se margine >+0.5, viceversa se <−0.5, 50/50 altrimenti; nessuna calibrazione claim.
- J2 ridge online alpha25 regolarizzata, StandardScaler solo train, almeno 18 precedenti mesi **maturi**. Stima mean signed F3−H1 log over next21 e sigma storico sul training (min 3%); peso 75/25 solo con segnale >0.5sigma, viceversa, altrimenti 50/50.
- J3 analoghi online KNN=8 su cinque feature standardizzate esclusivamente as-of e un precedente periodo maturo, stessa soglia 0.5sigma e peso 75/25/50. Niente tune ex post, nessun oracle tradable.
- Tutti ricostruiti con 10bp nominali per acquisto e per vendita, identico prossima apertura, quote effettivamente autofinanziate, merge ETF comuni, replay curve originali F3,H1,H3,50/50 nel limite 1e−9. Questo NON include spread broker, EUR FX, tasse o futures roll friction extra.

## Risultati economici definitivi, campione storico inquinato da ricerca precedente
| Metodo | CAGR 2021–26 netto nominale | MaxDD daily open | Sharpe log daily ×sqrt252 | Worst5% daily expected shortfall |
|---|---:|---:|---:|---:|
| F3 | 20.020% | −29.737% | .693 | −3.702% |
| H1 | 24.625% | −33.774% | .793 | −4.112% |
| H3 | 23.526% | −28.783% | .759 | −4.137% |
| **STATIC F3/H1 50:50** | **23.215%** | **−24.844%** | .887 | **−3.302%** |
| J1 margini del modello | 24.254% | −24.844% | .857 | −3.646% |
| J2 ridge prob. online | 23.878% | −24.844% | **.907** | −3.309% |
| J3 analoghi KNN online | 23.032% | −24.844% | .877 | −3.302% |
| Vecchio filtro Oil>Growth | 29.379% | −29.223% | .967 | −3.805% |
| Vecchio ridge 8 macro | 22.491% | −25.758% | .825 | −3.505% |

Il **29.38%** del filtro Oil/QQQ è noto come posthoc e fallisce gate a rischio equivalente; non confrontarlo come se dimostrasse alpha generale. J2 0.907 Sharpe marginalmente più alto ma ES 5% leggermente peggiore, +0.66pp CAGR non significativo contro 50/50, NO promozione.

## Previsione mensile relativa: il vero test è NEGATIVO
Solo 45 periodi (dopo warm-up con almeno 18 esempi interamente maturi) misurano i due modelli online.
- MSE matured historical mean signed differential **.00351045**; J2 Ridge **.00392904** e J3 KNN **.00371684** (entrambi PEGGIORI).
- Segno F3 supera H1: Brier del prior maturato **.259258** vs J2 **.288180**, J3 **.269521** (entrambi PEGGIORI). J2 sign accuracy **37.78%**, J3 **46.67%** (soglia p>=.5). J2 prediction/actual Pearson correlation **−.1131**, J3 **−.1670**. J2 prior Brier−J2 Brier gap −.02892 con 95% 3-anchor CI **[−.05087,−.00563]**: la previsione del segno è **significativamente peggiore** del semplice prior nell'ambito di questo dataset.
- J2 decide pesi diversi dal 50/50 soltanto **5 mesi su 64** (59 mesi 50/50; sui 45 dopo warmup esattamente 5 cambi) e "sceglie" l'esperto con payoff migliore in **3/5** di quei mesi. J3 in **2 mesi** (1/2 giusti). Non dichiarare vantaggio di regime dal suo lieve aumento Sharpe.
- J1 invece cambia pesi in 45/64 mesi, sceglie la direzione superiore solo in **22/45** attivazioni, quindi meno del 50%: il CAGR 24.25% deriva da singoli mesi/grandezze payoff, non dalla prevedibilità affidabile.

## Confronti statistici: intervalli annullano il vantaggio
Differenze *medie log net per 21 sedute* vs vero 50:50:
- J1 **+.000702**, 95% block CI **[−.002625,+.004477]**; 2021–23 positivo +.001353, 2024–26 **−.0000844** (fallimento incrociato);
- J2 **+.000448**, CI **[−.000288,+.001367]**; 2021–23 negativo −.000263, 2024–26 positivo +.001308;
- J3 **−.000124**, CI **[−.000867,+.000497]**; 2021–23 positivo, 2024–26 negativo;
- **Tutti i pre-registrati gate congiunti = FAIL**. Un miglioramento micro di CAGR non basta a certificare una probabilità/calibrazione di selezione.

## Perché falliscono e come procedere scientificamente
1. Sebbene F3 e H1 possiedano risultati storici diversi, **non è detto che il prossimo periodo di superiorità sia previsto** dalla sola composizione del portafoglio e dai loro score: sono proxy derivati dalla stessa serie prezzi passati; non arrivano veri segnali esogeni. Un filtro "conosco l'ultimo vincitore" ha già fallito.
2. `n=45` previsioni online dopo warm-up è piccolissimo per 10 dimensioni con regimi non stazionari; modello ridge molto shrink e l'analogo high-dimensional perde. F3/H1 risultano entrambi esposti a rischi che cambiano (petrolio futures roll, tecnologia, credito, equity).
3. **Serve una variabile causale non ottenuta rielaborando gli stessi prezzi**: curva futures petrolio/carry/backwardation con timestamp originale, variazione reale degli spread IG/HY, real yields, shock volatilità implicita VIX term structure, settore e leverage effettivi sotto il fondo, valuta e costi di esecuzione. Senza release times e correzione PIT, un apparente miglioramento ricadrebbe nel data leakage.
4. **Congelare i pesi statici 50/50 come controllo primario**, con H1, H3 e vecchio filtro USO/QQQ sotto controllo, e J2/J3 come esperimenti FALLITI. Niente ricerca di un nuovo lookback 35/42/84, 20%–80% o "miglior peso" sullo storico già testato: sarebbe iperottimizzazione.
5. Prossimo salto predittivo: **nuovi dati mai visti**, con registrazione timestamped degli score generati prima della decisione e 21 sedute di etichetta completamente matura, vero portafoglio ETF investibile e confronto broker/FX/rischio. Se non disponibile, il portafoglio storico 50/50 resta la baseline per una validazione PAPER, non capitale live.

## Procedura/fonte dei risultati
Action GitHub completata con success: https://github.com/AM1975MA/Test/actions/runs/39263599730 (un primo job di test fallito per uso improprio tuple/list negli indici NumPy, corretto **senza modificare né features né parametri** prima di produrre i risultati).
Scritti `PREREGISTERED.md`, `run.py`, `test_run.py`, `results/RESULT.json`, `results/FROZEN_64_ASOF_EXPERT_RELATIVE_FEATURES_PROB_AND_DECISIONS.csv`, `results/COSTED_DAILY_PORTFOLIOS_AND_KNOWN_CONTROLS.csv`, `results/SHA256_MANIFEST.txt`. Repo di produzione `etf_trader` inalterato.

**Verdetto definitivo di questa fase:** la complementarità F3/H1 serve a **diversificare**, non è stato ancora possibile trasformarla in un vantaggio temporale prevedibile. La soluzione candidata più robusta del campione resta 50/50 costed, finché prove prospettiche nuove non dimostrano altrimenti.
