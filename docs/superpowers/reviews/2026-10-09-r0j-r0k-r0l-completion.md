# ETF Trader V2 — R0-J/R0-K/R0-L: Conclusione verificata e prossimo gate

**Data:** 9 ottobre 2026. **Repository:** `AM1975MA/Test`, branch `research/v2-xgb-immutable-checkpoints-20261008`. **Stato:** rapporto e prototipo di ricerca completati; modello V2 produttivo invariato; nessun backtest finanziario rifatto.

## Risultato significativo — ma non ancora validazione economica

Un obiettivo pairwise che **ignora in training soltanto le coppie con differenze di rendimento minime** è una strada *tecnicamente realizzabile*. Non richiede una riduzione generalizzata dei 125 input, dei 360 alberi né delle foglie. Il principio è preservare comparazioni ad alta separazione economica, evitando che revisioni impercettibili degli Open rettificati cambino il segno di un confronto di ranking.

**Il dato realmente osservato non è un CAGR:** gli otto confronti Compact21 la cui rilevanza intera inverte l'ordine fra Yahoo Repeat1/Repeat3 sono tutti separati da **non oltre 0,0115991 punti base** nei rendimenti Open-to-Open a 21 sedute. **Nessuno** comprende un ticker nel decile più elevato della rilevanza di training (massimo percentile 80,54%). Sono dati storici già utilizzati nello sviluppo: il test è diagnostico, non un nuovo holdout.

## R0-J — Analisi estesa delle coppie sui due storici congelati

| Fonte / verifica | Risultato |
|---|---:|
| Mesi di training price-derived ricostruiti | **267** |
| Coppie ETF effettivamente confrontabili | **2.333.613** |
| Inversioni strette di rilevanza Compact21 | **8** |
| Parità create / parità eliminate | **7 / 7** |
| Coppie a distanza inferiore a 10 bp, Repeat1 | **45.181 (1,9361%)** |
| Coppie a distanza inferiore a 20 bp, Repeat1 | **88.417 (3,78885%)** |
| Inversioni di segno rimaste tra le coppie ammesse in almeno una delle due vintage, banda 20 bp | **0** |
| Cambiamenti di *ammissibilità* di una coppia vicino a 20 bp | **14** |
| Coppie eliminate che coinvolgono almeno un ETF top-decile | **2.373** |
| Coppie eliminate fra un top-decile e un bottom-quartile | **0 su 118.939** |

**Importanti restrizioni interpretative:**
1. **20 bp è una *ipotesi*, non la soglia ottimale né una verità economica.** L'origine è l'assunzione V2 0,1% per lato; ma il costo sostenuto nella scelta di A e nella scelta di B può essere comune alle due alternative, quindi non si può equiparare meccanicamente costo roundtrip e indifferenza predittiva fra due ETF. La soglia non deve essere adottata senza controllo indipendente di noise floor, market impact e obiettivo di trading.
2. **Zero inversioni ammesse è in parte atteso matematicamente** perché la soglia 20 bp è enormemente più ampia delle revisioni osservate, dell'ordine di centesimi di punto base. Ciò prova la fattibilità di un filtro di coppie, non una nuova capacità predittiva.
3. I 2.333.613 confronti sono la combinatoria teorica su ETF disponibili per ciascun mese, **non** i veri confronti estratti, campionati e pesati nell'algoritmo XGBoost `rank:pairwise`. Un filtro sulla lista teorica non implica automaticamente 3,79% di gradiente eliminato.
4. Conservare top-decile-vs-bottom-quartile non implica conservare tutte le discriminazioni importanti nella **coda positiva**: 2.373 confronti che toccano almeno un top-decile sono esclusi, inclusi confronti fra top ETF.
5. Prezzi Yahoo erano revisioni scaricate successivamente, **non as-of storici**. L'applicazione *live* futura richiede verifiche sull'età delle etichette e sulle revisioni del provider.

**Fonti:** `ETF_R0J_pair_details.csv`, `ETF_R0J_fee_band_results.json`, `ETF_R0J_material_invariance_results.json`, tutti nel pacchetto allegato. Sintesi strutturata già archiviata in GitHub: [`real_market_pair_statistics.json`](../../../target_redesign_level2_v1/stability_program_v2/r0j_r0k_r0l/real_market_pair_statistics.json).

## R0-K — Sostituzione generalizzata dell'obiettivo: non promuovere

Un solo candidato `rank:ndcg` con `ndcg_exp_gain=false`, stessa profondità, 360 round, tre seed, 125 feature, senza cambiare le altre variabili, è stato confrontato *solo sinteticamente* con `rank:pairwise`.

| Mondo A, 12 query indipendenti | `rank:pairwise` | `rank:ndcg` |
|---|---:|---:|
| Scelte Top1 nel vero Top5 artificiale | **11/12** | 10/12 |
| Scelte Top1 corrette come vincitore esatto artificiale | **7/12** | 5/12 |
| NDCG@5 sulla rilevanza sintetica | **0,93374** | 0,90224 |
| Top1 concorde dopo X-only | 9/12 | **12/12** |
| Top1 concorde dopo Y-only | 10/12 | **12/12** |

**Mondo B — completamento senza ripetizioni:** dopo l'interruzione sono stati allenati *solo* i **9 booster `rank:ndcg` mancanti**. Il loro baseline è **9/12** Top1 nei veri Top5, **4/12** vincitori esatti e NDCG@5 **0,80966**; concordanza X-only **12/12**, Y-only **9/12**. I nove booster `rank:pairwise` del mondo B risultavano già fittati prima dell'interruzione, **ma i loro score non furono salvati**: il confronto matched nel mondo B è **indeterminato**; non li ho riaddestrati, in coerenza col divieto di rifare test.

**Verdetto:** `rank:ndcg` **NON GO come sostituzione generale** sulla base dei dati disponibili. Non dimostra di mantenere la cattura delle opportunità. I due mondi sono giocattoli matematici, non rendimenti ETF. Risultati recuperati in [`r0k_synthetic_checkpoint.json`](../../../target_redesign_level2_v1/stability_program_v2/r0j_r0k_r0l/r0k_synthetic_checkpoint.json).

## R0-L — Obiettivo mascherato implementato e verificato, soltanto di ricerca

Il modulo [`cost_pairwise.py`](../../../target_redesign_level2_v1/stability_program_v2/r0j_r0k_r0l/cost_pairwise.py) implementa una loss logistica sui soli confronti ammissibili di **target di rendimento futuri già maturati**, gruppi mensili `group_ptr`, gradiente e Hessiana diagonale positiva. Gli asset con differenze superiori alla banda rimangono confrontati.

- **8 test unitari**: scelta delle coppie, invertibilità delle coppie escluse, gradiente contro differenze finite, gestione gruppo senza coppie, limiti di banda, input invalidi, allineamento gruppi e fit sintetico; **PASS** in locale.
- **XGBoost 3.1.3 `QuantileDMatrix`**: 12 round sintetici, **PASS**, prediction finite e non costanti.
- I risultati precedenti non validavano i gradienti numericamente: questa verifica matematica è stata aggiunta durante il completamento.
- Un'ulteriore verifica TDD di portabilità ha rilevato due path locali assoluti nello script R0-K; sono stati corretti nella copia riproducibile: **RED→GREEN**, ora 3 test R0-K locali superati.

**Limiti ingegneristici decisivi:** non è la loss nativa di XGBoost. Campiona tutte le coppie ammesse e approssima diagonalmente la curvatura; non replica la politica nativa di coppie, la normalizzazione e il peso degli errori. Non include ancora l'autorizzazione as-of/label-maturity sull'input, il contratto 125-feature del produttore, il versioning degli stati MA3, uno stress su X e Y indipendenti, né un confronto economico sul motore V2 completo. **Non copiare in produzione.**

## Proposta di sviluppo vincolata a nuove prove, non una caccia a CAGR

1. **P0: contratto di training e congelamento del modello per vintage, senza congelare la capacità di nuovo REFIT**, puntuale su universo, 125 feature, query, label exit mature, XGB 3 seed×2 orizzonti e modelli/stati MA3, versioni sorgente/runtime.
2. **P1: implementare in `Test` uno *shadow worker* pairwise robusto che non sostituisca il worker canonico**. Valutare l'esatto obiettivo rispetto a `rank:pairwise`, verificare ottimizzazione, scala del gradiente/Hessiana, stabilità del campionamento e conservazione dei confronti che coinvolgono gli ETF con alto upside. La banda non va selezionata sul CAGR 2017–2026. La banda di 20 bp è un prototipo; il noise floor provider ha una scala molto minore, quindi la motivazione della banda deve essere definita **prima di osservare P&L di nuove date**.
3. **P2: un solo confronto sintetico pre-registrato**, nuove fixture indipendenti, 360 round e tre seed, quattro casi baseline/X-only/Y-only/X+Y, verificando sia ranking stability sia Top5/tail capture. Se perde upside anche solo in una condizione importante, **STOP**.
4. **P3: primo eventuale test finanziario** soltanto su **date realmente nuove** con input point-in-time e labels maturi, comparando a pari mercato/universo originale e challenger con il **motore V2 completo** (MA3, 21/63, gestione rischio e costi invariati), CAGR/vintage se sufficiente storico, daily MaxDD, turnover, fee, code eccezionali. Se il campione è troppo breve, mostrare equity e P&L, non un CAGR annualizzato fuorviante.
5. **Champion/challenger**: un modello nuovo è ammesso se non degrada economicamente con margini predefiniti; in caso contrario resta la V2 originale. Nessun accordo su 20 bp o un miglioramento statistico sui due storici già esplorati costituisce un risultato finanziario.

**Dato importante raggiunto:** esistenza effettiva delle coppie di ranking invertite solo entro rendimenti trascurabili e disponibilità di un obiettivo che può neutralizzarle *in linea di principio*. **Non ancora raggiunto:** dimostrazione con dati ETF nuovi che la perdita di CAGR o l'instabilità XGB siano risolte. Le perturbazioni del train X da sole erano già responsabili di grandi differenze: un rimedio solo alle etichette potrebbe essere insufficiente.

### QA e fonti

Repository GitHub Test contiene lo script sperimentale, test e JSON di audit; il pacchetto conversazionale [`ETF_Trader_V2_R0J_R0K_R0L_Completato_20261009.zip`] conserva gli script completi R0-J e R0-K, risultati integrali/parziali, fixture sintetica R0-H, log, 33 transizioni CSV e report. SHA256 del ZIP aggiornato: `ab28c8a7009cbede1c5d02fdcd052886fc54625cc283e5c46ff1b44c134ef1ef`. Integrità archivio PASS, **24 file**, incluse le dipendenze R0-G/R0-H e la guida di riproducibilità. I 75 MB di prezzi Yahoo Repeat1/3 NON sono inclusi: sono i dati congelati della ricerca precedente, con SHA256 `fcc02918b3a42c3fecde273c4639ca4eed1b5f31e4b8c32aeea4c2a8e4c00f86`. Nessun modello produttivo modificato, nessun replay storico completato in questo turno.
