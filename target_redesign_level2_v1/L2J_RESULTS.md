# L2-J — Test del bootstrap temporale di XGBoost (8 ottobre 2026)

**Stato: COMPLETATO — AUDIT PASS — NO GO. Nessun modello promosso.** Tutte le modifiche GitHub riguardano esclusivamente `AM1975MA/Test`, branch `research/target-redesign-level2-v1`. Nessuna modifica a `Etf_trader`. Lo storico Original149 è già stato esplorato ripetutamente: questi risultati non costituiscono una conferma realmente indipendente.

## Test registrato prima di osservare i risultati

Protocollo: [L2J_PREREGISTRATION.md](L2J_PREREGISTRATION.md), commit `d0d11b72f569a877010110318a7d5e92adfaa9a2`.

- Fonte dati: tre acquisizioni Yahoo congelate dell'identico storico Original149, [GitHub Actions run 37121749852](https://github.com/AM1975MA/Test/actions/runs/37121749852), artifact `11272972639`, SHA256 ZIP `fcc02918b3a42c3fecde273c4639ca4eed1b5f31e4b8c32aeea4c2a8e4c00f86`.
- 149 ETF e 125 feature canoniche, Open aggiustati Yahoo, target rank percentile 21 sedute maturate prima dei cutoff annuali. **BIL escluso come benchmark dei target**, ma mantenuto come normale ETF eleggibile.
- 54 fit = 6 anni 2021–2026 × 3 acquisizioni × 3 modelli XGB. Rank:pairwise, 360 round, seed `101/202/303`, parametri canonici del modello precedente, salvo ricampionamento.
- Moving-block bootstrap di mesi di training in blocchi di **6 mesi**, con reinserimento fino al 100% della lunghezza storica, gruppi ETF/data mantenuti integri; sequenze casuali dei blocchi identiche fra acquisizioni per coppia anno/seed. Le tre previsioni vengono normalizzate a percentile intradata e mediate; rispetto al canonico cambia quindi anche l'aggregazione, e non è possibile attribuire causalmente tutto il differenziale al solo bootstrap.
- Valutazione su **66 date mensili mature** gennaio 2021 – giugno 2026; 29.502 righe mature (66×149×3). 29.949 score per ramo nativo o input comune, inclusi i 447 score luglio 2026 senza risultato futuro.
- Basi già congelate L2-D: XGB originale e Ridge(alpha=30). Tre acquisizioni Yahoo sono **lo stesso mercato**, non tre osservazioni campionarie indipendenti.

## Risultati predittivi: medie per data, media vintage entro data

| Indicatore | XGB originale | BOOTSTRAP3 | Ridge |
|---|---:|---:|---:|
| NDCG@5 | 0.569350 | **0.516963** | 0.571810 |
| Rank IC | 0.070994 | **0.051498** | 0.114004 |
| Primo ETF scelto tra i Top 5 reali | 21.2121% | **22.7273%** | 13.6364% |
| Rendimento netto medio ETF scelto a 21 sedute | **+3.3914%** | +1.9451% | +2.3999% |
| Percentile del rendimento realizzato | 0.614026 | 0.546810 | 0.571283 |

Il miglioramento di Top5 hit di BOOTSTRAP3 vs XGB è solo **+1.52 punti percentuali** (non conclusivo). Il NDCG@5 scende di **-0.05239**; intervallo bootstrap descrittivo 95% **[-0.08857, -0.01851]**. Il ritorno medio scelto scende di **-1.446 punti percentuali**, intervallo descrittivo **[-3.286, +0.273] punti percentuali**, attraversa zero. Intervalli con paired moving block bootstrap 3 mesi, 10k repliche, senza correzione per multipli test; non sono una conferma prospettica.

## Instabilità tra train Yahoo: input inferenza comune Repeat2

| Confronto | BOOTSTRAP3 Top1 agreement | XGB originale | Ridge | BOOTSTRAP3 rank-MAD |
|---|---:|---:|---:|---:|
| repeat1/repeat2 | **40.91%** | 42.42% | 100% | 0.05877 |
| repeat1/repeat3 | **31.82%** | 57.58% | 100% | 0.05765 |
| repeat2/repeat3 | **37.88%** | 51.52% | 100% | 0.05915 |

In input native sono quasi identici: le divergenze sono causate prevalentemente dal **fitting**, non dalla perturbazione dell'input di inferenza.

**Leave-one-member-out all'interno del bootstrap**: rimuovere un membro cambia il primo ETF nel **42–51%** delle date per vintage; una debolezza strutturale aggiuntiva del nuovo committee. Ogni bootstrap contiene mediamente soltanto **63.6% mesi distinti** del training originale, dato il campionamento con replacement; possibile fonte di elevata varianza, non prova causale esclusiva.

## Econofisica: regime di volatilità precedente SPY (solo diagnostico)

Il regime è HIGH se la volatilità SPY realizzata nelle ultime 21 sedute supera la mediana dei 36 mesi precedenti; altrimenti LOW. Classificazione esclusivamente retrospettiva, causalmente disponibile al signal time. Campione di **38 date LOW**, **28 HIGH**:

| Metrica | LOW | HIGH |
|---|---:|---:|
| XGB ritorno medio 21d | +2.529% | +4.562% |
| BOOTSTRAP3 ritorno medio 21d | +1.950% | +1.938% |
| XGB Top5 hit | 14.91% | 29.76% |
| BOOTSTRAP3 Top5 hit | 21.93% | 23.81% |

Il bootstrap perde il rendimento storicamente elevato di XGB nelle date HIGH, pur catturando alcuni Top5. Nessuna regola di regime viene ricavata o ottimizzata da questi risultati.

## Replay economico Top1 semplificato (NON Hybrid24)

66 scelte 2021–2026, acquistare il Top1 alla prima apertura disponibile dopo il segnale, ribilanciare all'apertura successiva dopo il segnale seguente, ultimo mese detenuto sino all'exit Open già maturato. Costi **0.1% per ogni acquisto e vendita effettivi**, no costo terminale inventato, capitale composto; DD valutato solo sui saldi mensili, non sugli estremi intramese. 5.492 anni di capitale investito.

| Yahoo repeat | XGB CAGR proxy | BOOTSTRAP3 CAGR proxy | Ridge CAGR proxy | BOOTSTRAP3 max DD mensile |
|---|---:|---:|---:|---:|
| 1 | 28.00% | **9.34%** | 25.77% | -53.34% |
| 2 | 35.18% | **21.93%** | 25.77% | -43.18% |
| 3 | 46.72% | **16.95%** | 25.77% | -26.32% |

Questi risultati non sono una replica della strategia Hybrid24 né un'indicazione del rendimento futuro; non includono rischio intramese, tutti i basket/governor, slippage, tasse, ecc.

## QA indipendente

**PASS** su 54 fit, 29.949 score per ramo senza duplicati, train exits strettamente precedenti al cutoff, stessi SHA delle schedulazioni bootstrap fra vintage per anno/seed, input common Repeat2/nativo Repeat2 identico, verifiche Open-to-Open su 200 righe (errore max 9.89e-17), 37 scelte Top1 ricalcolate autonomamente, **9 portafogli e 594 periodi di negoziazione** ricalcolati con errore capitale massimo **4.89e-15**.

Codice e dati intermedi riproducibili nel pacchetto conversazione `ETF_Trader_L2J_block_bootstrap.zip` (25 file ZIP validati, script `l2j_run.py`, `l2j_evaluate.py`, `l2j_audit.py`, derivazione feature e native/common predictions). I prezzi grezzi restano disponibili nell'artifact GitHub citato; il pacchetto non li duplica.

## Verdetto

Gate fissato **prima dell'esperimento**: Top1 agreement common-input>=85% su ciascuna coppia, rank-MAD native <0.02, hit Top5>=15%, selected 21d return >=Ridge. **Solo il criterio Top5 è superato; gli altri tre falliscono.**

**NO GO; nessuna promozione, nessuna variazione al repo Etf_trader.** Non testare altri parametri bootstrap sul medesimo Original149 per cercare ex post CAGR. Per un passaggio reale serve una nuova prova su periodo e snapshot acquisiti *prospetticamente*, con protocollo congelato.