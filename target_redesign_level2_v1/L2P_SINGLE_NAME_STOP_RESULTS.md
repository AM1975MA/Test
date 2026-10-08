# L2-P — Stop specifico degli ETF indipendente dallo stress sistemico

**Data: 2026-10-08. Concluso, audit indipendente PASS, NO GO.** Solo `AM1975MA/Test`, branch `research/target-redesign-level2-v1`; `Etf_trader` non modificato. [Protocollo preregistrato prima di qualsiasi risultato](L2P_SINGLE_NAME_STOP_PREREGISTRATION.md), commit `d1ca4cf0f05525fe935874b8b81bbfdadb3b7f5f`.

## Unico intervento testato

Sull'intera V2 Annual/MA3/HighCAGR24/DDfirst/V6/Stage19, 149 ETF, Yahoo Repeat2 frozen, 2.366 sedute 2017-02-01—2026-07-01, costi 0,1%, **rimuovere soltanto il test di stress del mercato** dai due stop delle posizioni top1 e top2:

```python
# Prima (BASE)
if t1>=0 and u1>0 and p1 and (sysm or ud1[k]>=.55):
# Dopo (L2-P)
if t1>=0 and u1>0 and p1:
# Identica sostituzione per t2/u2/p2.
```

`p1` e `p2` restano i segnali tecnici pregressi UH/SA. Inalterati stop **5,5% rispetto al Close precedente**, fill Open se gap oltre livello, altrimenti stop×(1−0,001) se Low tocca, commissioni 0,001, cooldown del rischio 3 giornate, re-entry originale, ranking, pesi, cash BIL/SHV, GALT e V6. Il protocollo ha fissato **quattro gate congiunti**: CAGR>=95% BASE, DD migliorato >=2pp, turnover<=110% BASE, audit PASS. Non aggiustare alcun valore sullo storico utilizzato.

## Risultati economici — V2 completa, non Top1 proxy

| Indicatore | Originale | L2-P | Delta |
|---|---:|---:|---:|
| CAGR | **30,8437%** | 25,9749% | **−4,8688 pp** |
| MaxDD **giornaliero** | **−25,6896%** | −33,0970% | **−7,4074 pp** |
| Sharpe | **1,0870** | 0,9695 | −0,1175 |
| Capitale finale (base 1) | 12,478988 | 8,740862 | −29,96% relativo |
| Turnover annualizzato | **12,9605×** | 16,4580× | +26,99% |
| Stop effettivamente eseguiti | 20 | 48 | +28 |
| Somma commissioni pagate (unità capitale iniziale)* | 0,519302 | 0,712599 | +0,193297 |

\* Commissioni reali modellate nei due ledger su capitali di diversa grandezza, non percentuali confrontabili direttamente.

**ALL-pass gate: FAIL** su CAGR, MaxDD e turnover; PASS audit. Blocchi bootstrap paired (113 mesi, blocchi 3 mesi, 5000 ricampionamenti): delta log-return medio mensile −0,3151 pp; 95% descrittivo [−0,6152,−0,0388] pp. Le molte prove precedenti rendono questi intervalli non idonei alla validazione prospettica.

## Causa osservata: non basta eseguire stop senza governare il rientro

Identico worst drawdown temporale in BASE e L2-P: valorizzazione agli Open **20 giugno–8 ottobre 2025**, riportata dal vecchio ledger come 18 giugno–7 ottobre. Base **−25,69%**, L2-P **−33,10%**. L2-P esegue **sei stop su UNG** dentro questo intervallo: 30/6, 9/7, 23/7, 4/8, 12/8 e 19/8; la base nessuno.

Un evento stop porta il ricavato in `free`, ma al successivo Open la clausola `free>0` in `simulate_arch` **forza un nuovo ribilanciamento sugli ETF ancora selezionati**. In 43 giornate successive agli eventi stop si osserva un nuovo ribilanciamento. Lo stop quindi può portare a stop/rebuy/stop, costi e whipsaw; il cooldown riduce la gross exposure ma non impedisce il riacquisto del ticker. Nessuna correzione automatica alla politica di rientro è stata progettata o ottimizzata in questo test.

## Qualità e integrità

- Esatto match della BASE indipendente già congelata Repeat2: `CAGR=0.3084370492564604, maxDD=-0.256896102666868, Sharpe=1.0869929498969455`, errori <3.4e−16.
- **Numba V2 vs motore monetario Python indipendente** (identiche due condizioni cambiate): differenza max equity **0**, max turnover **0**, contabilità giornaliera residuo <1.78e−15, su 2.365 periodi, 2.366 saldi.
- **48/48** stop verificati indipendentemente su Close precedente e adjusted OHLC, inclusi **10** fill ai gap Open; fee esatte secondo policy.
- Dati Yahoo erano scaricati nel 2026: non vere vintage point-in-time; trade reali con spread, profondità e sequenza intraday non replicati. Original149 **storico di ricerca consumato**, non test indipendente.
- Golden Annual V2 **43,145952%** proviene da altra vintage e qui **non** costituisce baseline matched. La differenza Golden vs Repeat2 non va attribuita a L2-P.

**Decisione:** NON promuovere questa variante. Prima di altri esperimenti occorre separare esplicitamente `segnale di invalidazione dell'ETF`, `stato di uscita dalla posizione`, `condizione di rientro`. Non cambiare soglie o cooldown post hoc sul 2025. Per passare in produzione, valutazione prospettica con nuovo snapshot causale.

**Riproducibilità:** eseguibili completi `l2p_run.py` e `l2p_independent_audit.py`, giornalieri, stop, ledger, bootstrap e manifest nel pacchetto `ETF_Trader_L2P_stop_individuale_V2.zip` fornito in conversazione; dipendenze: `titanium-repeat-2.zip` e sorgenti L2-N/L2-O già congelati. SHA256 archivio L2P `6b307340022c6ac4a122e36bcc161dab9465c6250c0d7ad036a4abdf0e444410`, 15 file ZIP integri.
