# OLC63 — Perché la fusione originale supera i nuovi learner: attribuzione e interazioni

**7 novembre 2026. Ricerca diagnostica, NO PROMOTION.** Nessuna nuova regola di trading, modello riaddestrato o modifica a `main`/OLC19. I dati 2019–2026 sono stati ampiamente esplorati in precedenza, quindi non sono una validazione fuori campione indipendente.

## Conclusione

La fusione originale sfrutta la **complementarità dei componenti**. In Europa domina il contributo di **Extra Trees (ET)** e, condizionatamente a ET, quello della **memoria temporale**. Negli USA il contributo individuale più ampio su 2021–2024 è **RETURN**, ma è concentrato soprattutto nel 2022, mentre ET e XGB alternano periodi positivi/negativi. Nessuno di questi risultati consente di impostare nuovi pesi dinamici validati.

### Ricostruzione originale — parità completa

Funzione fedele:

- `CURRENT = 0.60 * rank_pct(ET) + 0.40 * rank_pct(XGB)`;
- `SMOOTH = clip(0.40 * CURRENT[t] + 0.30 * CURRENT[t-1] + 0.30 * CURRENT[t-2], 0, 1) ** 1.1` (rinormalizzazione originale per lag mancanti);
- `FUSION = 0.475 * RETURN + 0.525 * SMOOTH`.

Parità numerica per score Current/Smooth/Fusion con il checkpoint OLC14 (errore massimo ≤ 2,3e-16). **180/180 coppie Top2** del checkpoint OLC19 coincidono (90 EU, 90 USA). Validati gli SHA256 dei tre ZIP di input; nessun refit. Gli effetti di componenti abilitati/disabilitati sono valutati sulla stessa eleggibilità ETF originale, mai sui label futuri. Null feature: valore neutro `0.5` costante, pesi originali non rinormalizzati. Non significa che il componente sia economicamente assente in un sistema totalmente riaddestrato.

### Contributo medio Shapley all'uplift Top2 vs portafoglio uniforme — MAIN 2021–2024

I valori sono punti percentuali di **rendimento statico Open→Open** su un orizzonte di 21 sedute, non CAGR né contributi al P&L della strategia completa:

| Fattore | EU | USA |
|---|---:|---:|
| RETURN | +0,362 | +1,498 |
| ET | +0,597 | +0,752 |
| XGB | +0,181 | +0,502 |
| Memoria | +0,448 | +0,220 |
| Somma uplift | **+1,588** | **+2,972** |

Verifica di coerenza: EU media Top2 2,1309%, media universo 0,5432%; USA Top2 3,5010%, universo 0,5291%. Intervalli circolari bootstrap di 6 mesi, **descrittivi**, 2021–2024: ET EU [0,119; 1,102] pp; RETURN USA [-0,195; 3,418] pp; entrambi non corretti per tutte le analisi svolte.

### Ablazione condizionata a tutti gli altri componenti

Si toglie una parte alla volta dal FUSION originale (quindi cambia il ranking), lasciando tutte le altre intatte. Numeri = media `con componente - senza componente` su 48 mesi, 21 sedute:

| Parte rimossa | EU: beneficio di tenerla | EU: mesi Top2 cambiati | USA: beneficio di tenerla | USA: mesi Top2 cambiati |
|---|---:|---:|---:|---:|
| RETURN | +0,389 pp | 35/48 | +1,868 pp | 39/48 |
| ET | **+1,016 pp** | 31/48 | +0,543 pp | 29/48 |
| XGB | +0,016 pp | 22/48 | +0,194 pp | 25/48 |
| MEMORIA | **+1,094 pp** | 37/48 | +0,404 pp | 38/48 |

L'ablation XGB sul MAIN cambia concretamente coppie pur migliorando pochissimo il rendimento in media: indica **potenziale ridondanza nel contesto congelato**, non autorizza a eliminarlo. La memoria europea produce un impatto condizionato molto più grande del suo Shapley medio, coerentemente con interazioni significative.

### Interazioni a due fattori: Shapley interaction index

Questa è la nuova diagnostica aggiuntiva (post-risultato) su tutti i 16 sottoinsiemi già congelati, non un nuovo esperimento di trading. Ogni interazione è calcolata con le differenze seconde mediate sugli altri sottoinsiemi. Valori: punti percentuali del rendimento Top2 a 21 sedute, MAIN 2021–2024.

| Coppia | EU | USA |
|---|---:|---:|
| ET × Memoria | **+0,824** | -0,157 |
| XGB × Memoria | +0,164 | +0,189 |
| RETURN × Memoria | +0,106 | +0,371 |
| ET × XGB | **-0,246** | **-0,349** |
| RETURN × ET | -0,197 | +0,219 |
| RETURN × XGB | -0,018 | **-0,460** |

Un'interazione negativa significa che il rendimento della combinazione non è la somma dei miglioramenti individuali rispetto al sistema neutro sotto questa specifica neutralizzazione. **Non** dimostra una relazione economica causale e non autorizza l'eliminazione di un componente. Gli indici di interazione non vanno sommati alla tabella Shapley come extra alpha.

### Ridondanza e stabilità

Correlazione Spearman media tra rank ET e XGB: **EU 0,816; USA 0,806**. Tra RETURN e CURRENT modellistico: **EU 0,247; USA 0,455**. RETURN e CURRENT sono più complementari in Europa dal punto di vista della correlazione, mentre in USA segnalano esposizioni in parte sovrapposte. L'alta correlazione ET/XGB non dimostra da sola la ridondanza economica: conta l'effetto sulle scelte estreme.

Contributi Shapley annuali al rendimento Top2 a 21 sedute (pp/mese):

| Anno | EU ET | EU memoria | USA RETURN | USA ET |
|---|---:|---:|---:|---:|
| 2021 | +0,567 | -0,475 | +1,036 | +0,350 |
| 2022 | +1,153 | +0,570 | +4,737 | -1,024 |
| 2023 | +0,337 | +1,512 | +1,075 | +0,771 |
| 2024 | +0,332 | +0,184 | -0,857 | +2,912 |

EU ET è positivo in tutte e quattro le annualità, USA RETURN non lo è. Tuttavia, la forza di questi contributi è sensibile a mesi estremi. Per EU ET i migliori tre mesi valgono **13,07 pp-mese**, a fronte di contributo netto cumulato **28,67 pp-mese** nel MAIN; per USA RETURN i migliori tre mesi valgono **49,40** su **71,90 pp-mese** netti. Il secondo caso è molto più concentrato. Nello stesso periodo EU memoria +21,49 pp-mese netti, ma i migliori tre mesi ne rappresentano 18,26. Non usare risultati selezionati ex-post come regole di mercato.

### 2025: diagnostica separata, NON OOS

**EU 10 mesi validi**, poiché aprile/maggio 2025 hanno un'etichetta futura mancante per almeno un ETF eleggibile; **USA 12 mesi**. Sull'intervallo così filtrato la FUSION completa produce EU +0,363% contro +1,301% del portafoglio uniforme, USA +1,996% contro +1,912%.

Contributo marginale di **tenere** RETURN rispetto alla versione che lo esclude: EU **−0,447 pp** per mese; contributo di tenere ET: USA **−4,631 pp** per mese, nel 2025. Non è prudente impostare un gate differenziato del 2025 sulla base di questi risultati: mancano prova previsionale e periodo indipendente.

### Diagnostica degli head originali (non ablation diretta)

Su 2021–2024, rendimenti Top2 a 21 sedute: EU C21 blend +0,559%, C42 blend +1,152%, C63 blend +0,854%; USA C21 blend +2,217%, C42 blend +1,589%, C63 blend +1,201%. La **FUSION originale** supera tutte queste varianti isolate sui rispettivi mercati (EU +2,131%, USA +3,501%). Gli head 21/42/63 non sono componenti intercambiabili della formula FUSION: vanno interpretati come diagnostica descrittiva di orizzonte.

## Decisione

1. **NON cambiare pesi né rimuovere XGB oggi**: ablation/posthoc non equivale a nuovo alpha.
2. Priorità quantitativa: verificare se **segnali disponibili ex ante** (es. discordanza tra RETURN e CURRENT, instabilità del ranking, dispersione degli score) prevedono **il valore marginale futuro dei componenti**. Prima analisi di capacità informativa, senza integrare gate o timing nel trading.
3. Fermarsi se l'associazione predittiva non è robusta in EU, USA e nei sotto-periodi; eventuali successivi learner richiedono cutoff delle etichette e un periodo di validazione successivo non già esplorato.

## Riproducibilità e QA

- `run_olc63.py`: ricostruzione OLC14/16/19, 16 subset, Shapley sui 4 fattori, percentili, heads e correlazioni.
- `verify_olc63_independent.py`: ricalcolo indipendente via 24 permutazioni, parità conto con checkpoint OLC60 e Top2 originali.
- `analyze_component_interactions.py`: analisi *post-result* su CSV congelati, annualità, concentrazione, interazioni.
- `verify_interactions.py`: test indipendente via dividendi Harsanyi; **1416 interazioni** confrontate, errore massimo **1,25e−16**, e Shapley originale ricostruito con errore massimo **1,51e−16**.
- Sorgenti originali non inclusi nel pacchetto per evitare duplicazioni: salvati negli archivi di ricerca OLC14, OLC16 e OLC19 della Library. Protocolli/checksum registrati; report e dati CSV possono essere ricalcolati recuperando i tre ZIP parent.

**Nessun CAGR di questa attribuzione deve essere riportato o interpretato come nuovo rendimento della strategia.**