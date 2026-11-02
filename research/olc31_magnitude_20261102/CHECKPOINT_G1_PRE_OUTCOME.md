# OLC31 — G1, esperimento prima degli esiti

2 novembre 2026; `PROTOCOLLO_MAESTRO_IT.md` frozen al commit ce7b992e4ac175c3ca12c408ae842a3b74888b48. G0 completato e pubblicato prima di calcolare le associazioni G1. Il test G1 è descrittivo/diagnostico, senza fitting di modelli e senza backtest.

## Misure fissate prima di guardare i risultati
- Periodo principale 2021-01-01 .. 2024-12-31 (48 segnali); anni fuori periodo soltanto diagnostici, non holdout.
- Margine reale: differenza **log-return Open dell'intervallo mensile successivo** tra ETF nello stesso mercato e signal_date, non rendimento futuro di 21 sedute, no costo (è diagnostica lordo).
- Input: FUSION OLC20; raw OLC16 `C21_ET`, `C21_XGB`, `C42_ET`, `C42_XGB`, `C63_ET`, `C63_XGB`; raw OLC08 `RETURN_RAW`, `ET_RAW`, `XGB_RAW`. I diversi modelli non vengono confusi; per ognuno la differenza è solo entro il medesimo learner e mese.
- Endpoints: QDVE.DE/ARGT/SMH **non** sono filtri; baseline confronto Top2 e Top5 FUSION, secondariamente tutti i ticker; non si seleziona un periodo più favorevole.
- Metrica A: per ciascun market/month, correlazione Pearson degli score con il vero r_i Open→Open tra i cinque ETF Top5 AUTH; riportare la **media fra mesi** con supporto >=4, e l'intervallo bootstrap descrittivo per differenza contro la FUSION (6 mesi, 4000 draw, seed 20261102).
- Metrica B: Top1-versus-Top2 actual spread correlato in 48 mesi con lo spread `FUSION`, `RETURN_RAW`, `C21_ET`, `C21_XGB`, `C42_ET`, `C42_XGB`, `C63_ET`, `C63_XGB`. Riportare numeri mesi e gap medio reale, non un p-value che supponga iid.
- Metrica C: in ogni market-month Top5, calcolare 10 confronti ordinati per FUSION tra 5 ETF; quota concordanza sul segno e differenziale medio condizionato a quartili della differenza raw, ma pesare l'evento mensile non 10 come indipendenti.
- Placebo negativo: per ciascun raw score in Top5, mescolare i 5 valori fra ticker **della stessa data e mercato** con seed 31001..31005 (dopo aver fissato FUSION invariato), per preservare distribuzione/missingness e distruggere il legame raw→ticker. È una descrizione di controllo, non un test di exchangeability di mercato. Non scegliere seed favorevoli.
- Missing EU: tutte e due le aperture observed, escludere LEEU.DE nei due mesi 2024 dichiarati; missing USA: flag finiti positivi e nota quote non certificate. Righe 2020-04-30, 2020-05-29 segnalate come incomparabili in analisi full; 2026-06-30 terminale senza label.

## Cancelli
Se G1 non mostra alcun vantaggio sulle differenze economiche **condizionalmente ai rank** o i raw/placebo sono equivalenti, fermare B2 e cercare altri target senza chiamare questo miglioramento. Se uno o più raw sono promettenti, G2 è comunque necessario per confermare con calibrazione OOF cronologica; un correlation positivo in-sample NON basta e nessun Top2 viene cambiato in G1.
