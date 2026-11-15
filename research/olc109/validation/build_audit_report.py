"""Assemble the independent review only after both corrected audits finish."""
from pathlib import Path
import datetime
import hashlib
import json
import numpy as np
import pandas as pd


def read_json(path):
    return json.loads(Path(path).read_text())


def integer(value):
    return f"{int(value):,}".replace(",", ".")


def money(value):
    return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def run(root):
    root = Path(root)
    output = root / "validation"
    stages = ((1, ".", "results"), (2, "stage2", "results_stage2"), (3, "stage3", "results_stage3"))
    qa = [read_json(output / folder / "INDEPENDENT_QA.json") for _, folder, _ in stages]
    assert [q["paths"] for q in qa] == [110, 50, 40]
    assert all(q["financial_csv_float_parser"] == "round_trip" and q["status"].startswith("PASS") for q in qa)
    prefix = read_json(output / "PREFIX_CAUSALITY.json")
    tamper = read_json(output / "TAMPER_CONTROLS.json")
    precision = read_json(output / "CSV_PRECISION_REGRESSION.json")
    price_age = read_json(output / "PRICE_AGE_QA.json")
    analysis_review = read_json(output / "BOOTSTRAP_ANALYSIS_REVIEW.json")
    matched_review = read_json(output / "MATCHED_STATE_REVIEW.json")
    assert analysis_review["status"] == "PASS_ALL_ANALYSIS_AND_BOOTSTRAP_CHECKS"
    assert analysis_review["analysis_code_sha256"] == hashlib.sha256((root / "analysis/analyze_results.py").read_bytes()).hexdigest()
    assert analysis_review["financial_paths"] == 200 and analysis_review["paired_comparisons_checked"] == 16
    assert matched_review["status"] == "PASS_INDEPENDENT_MATCHED_STATE_REPLAY"
    assert matched_review["production_script_sha256"] == hashlib.sha256((root / "analysis/matched_state_trend_gate.py").read_bytes()).hexdigest()
    assert matched_review["intervals"] == 160 and matched_review["branch_replays"] == 320
    assert not matched_review["counterfactual_compounding"] and not matched_review["imports_production_code"]
    assert prefix["target_vectors_checked"] == 120 and prefix["status"].startswith("PASS")
    assert tamper["negative_controls"] == 6 and tamper["status"].startswith("PASS")
    assert precision["status"].startswith("PASS")
    f1, f2 = read_json(root / "docs/PROTOCOL_FREEZE.json"), read_json(root / "docs/STAGE2_FREEZE.json")
    m1, m2 = read_json(root / "results/RUN_MANIFEST.json"), read_json(root / "results_stage2/RUN_MANIFEST.json")
    f3, m3 = read_json(root / "docs/STAGE3_FREEZE.json"), read_json(root / "results_stage3/RUN_MANIFEST.json")
    time = lambda value: datetime.datetime.fromisoformat(value)
    assert time(f1["created_utc"]) < time(m1["start_utc"]) < time(m1["end_utc"]) < time(f2["created_utc"]) < time(m2["start_utc"]) < time(m2["end_utc"]) < time(f3["created_utc"]) < time(m3["start_utc"]) < time(m3["end_utc"])
    for manifest in (m1, m2, m3):
        for relative, expected in manifest["code_hashes"].items():
            assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected
        for relative, expected in manifest["data_hashes"].items():
            assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected
    reconstructions = []
    for stage, folder, result_folder in stages:
        reference = pd.read_csv(output / folder / "INDEPENDENT_RECONSTRUCTIONS.csv", float_precision="round_trip")
        reported = pd.read_csv(root / result_folder / "SCORECARD.csv", float_precision="round_trip")
        matched = reported.merge(reference, on=["path_id", "arm", "scenario"], suffixes=("_reported", "_reference"), validate="one_to_one")
        assert len(matched) == len(reference) == len(reported)
        for field in ("cagr", "cumulative", "maxdd_close", "maxdd_sampled", "calmar", "volatility", "worst_21_sessions", "end_equity", "days", "costs", "orders", "trading_days", "trading_days_per_year"):
            assert np.allclose(matched[field + "_reported"], matched[field + "_reference"], rtol=1e-10, atol=1e-8), ("SCORECARD_RECONCILIATION", stage, field)
        reference["current_cagr_target_pass"] = reference.cagr >= .30
        reference["stage"] = stage
        reconstructions.append(reference)
    reconstructions = pd.concat(reconstructions, ignore_index=True)
    assert len(reconstructions) == 200 and not reconstructions.path_id.duplicated().any()
    reconstructions.to_csv(output / "ALL_INDEPENDENT_RECONSTRUCTIONS.csv", index=False)
    trades = pd.concat([pd.read_csv(output / folder / "TRADE_PARTICIPATION.csv.gz", float_precision="round_trip").assign(stage=i)
                        for i, folder, _ in stages], ignore_index=True)
    source = pd.concat([pd.read_csv(output / folder / "LIQUIDITY_SOURCE_CHECKS.csv").assign(stage=i)
                        for i, folder, _ in stages], ignore_index=True)
    assert (source.status == "PASS").all()
    participation = []
    for label, frame in (("all_scenarios", trades), ("BASE_only", trades[trades.scenario == "BASE"])):
        participation.append(dict(scope=label, orders=len(frame), zero_or_unavailable_turnover=int((frame.raw_traded_eur <= 0).sum()),
                                  above_one_percent=int((frame.traded_value_participation > .01).sum()),
                                  above_ten_percent=int((frame.traded_value_participation > .10).sum()),
                                  above_full_daily_turnover=int((frame.traded_value_participation > 1).sum()),
                                  maximum_ratio=float(frame.traded_value_participation.max())))
    top = trades.nlargest(10, "traded_value_participation")
    top.to_csv(output / "LARGEST_TRADE_PARTICIPATION.csv", index=False)
    summary = dict(status="PASS_200_INDEPENDENT_ACCOUNTS_AND_SIGNALS", paths=200, stages=qa,
                   all_frozen_financial_code_and_inputs_unchanged=True, declared_stage_timestamp_order_checked=True,
                   unique_source_liquidity_instruments_checked=int(source["isin"].nunique()),
                   source_liquidity_rows_checked_including_cross_stage_rechecks=int(source.sessions_checked.sum()),
                   source_liquidity_unique_rows_checked=int(source["isin"].nunique()) * 1970,
                   order_quantities_and_timestamps_checked=sum(q["order_quantities_checked"] for q in qa),
                   independently_derived_instructions=sum(q["independently_derived_instructions"] for q in qa),
                   independently_derived_reductions=sum(q["independently_derived_reduction_signals"] for q in qa),
                   unique_cluster_snapshots_rebuilt=80, unique_groups_rebuilt=13528,
                   independently_derived_raw_selection_targets=sum(q["independently_derived_raw_targets"] for q in qa),
                   prefix_target_vectors_checked=120, tamper_controls_rejected=6,
                   numerical_residue_only_deferred_sessions=sum(q["numerical_residue_only_deferred_sessions"] for q in qa),
                   max_nav_cash_error=max(q["max_nav_cash_error"] for q in qa),
                   max_per_order_cost_error=max(q["max_per_order_cost_error"] for q in qa),
                   max_daily_pnl_attribution_error=max(q["max_daily_pnl_attribution_error"] for q in qa),
                   legacy_numeric_target_passes=sum(q["numeric_target_passes"] for q in qa),
                   legacy_full_target_passes=sum(q["full_target_passes"] for q in qa),
                   current_cagr_target_passes=int(reconstructions.current_cagr_target_pass.sum()),
                   current_cagr_base_passes=int((reconstructions.current_cagr_target_pass & reconstructions.scenario.eq("BASE")).sum()),
                   maximum_current_cagr_any_scenario=float(reconstructions.cagr.max()),
                   maximum_current_cagr_base=float(reconstructions.loc[reconstructions.scenario.eq("BASE"), "cagr"].max()),
                   trade_participation=participation, price_age=price_age,
                   analysis_verification=dict(monthly_returns_checked=analysis_review["monthly_return_rows_checked"],
                                              annual_returns_checked=analysis_review["annual_return_rows_checked"],
                                              annual_2024_rows_retained=analysis_review["annual_2024_rows_retained"],
                                              paired_comparisons_checked=analysis_review["paired_comparisons_checked"],
                                              all_descriptive_intervals_contain_zero=all(c["interval_contains_zero"] for c in analysis_review["comparisons"]),
                                              multiplicity_corrected=False, adaptive_holdout=False,
                                              artifact="validation/BOOTSTRAP_ANALYSIS_REVIEW.json"),
                   matched_state_verification=dict(intervals=matched_review["intervals"],
                                                   independent_branch_replays=matched_review["branch_replays"],
                                                   maximum_errors=matched_review["maximum_errors"],
                                                   counterfactual_compounding=False,
                                                   artifact="validation/MATCHED_STATE_REVIEW.json"),
                   economic_or_statistical_validity_certified=False,
                   caveat="Accounting and protocol correctness do not establish investability, causal out-of-sample performance, or achievement of the user target.")
    (output / "COMBINED_QA.json").write_text(json.dumps(summary, indent=2) + "\n")
    p_all, p_base = participation
    primary = top.iloc[0]
    lines = [
        "# OLC109 — Revisione indipendente di conti, segnali e fonti", "",
        "## Esito", "",
        "**PASS contabile e di conformità ai protocolli per tutti i 200 percorsi: 110 del blocco iniziale, 50 del secondo e 40 del terzo.** La correttezza del calcolo non costituisce validazione economica della strategia.", "",
        f"Il criterio attuale dell'utente è CAGR almeno 30%, con drawdown e Calmar descrittivi. I percorsi che raggiungono questo CAGR sono **{summary['current_cagr_target_passes']}/200**, inclusi **{summary['current_cagr_base_passes']}/40 nello scenario BASE**. Il migliore CAGR è **{summary['maximum_current_cagr_base']:.4%} in BASE** e **{summary['maximum_current_cagr_any_scenario']:.4%} tra tutti gli scenari**. I campi tecnici legacy che includono DD 25% e Calmar 1 vengono riconciliati senza trattarli come criterio corrente di esclusione.", "",
        "I file di protocollo, il codice finanziario e i dati conservano gli hash registrati prima dei rispettivi run. Le date registrate ordinano ogni congelamento prima della relativa esecuzione e dopo l'osservazione del blocco precedente. I blocchi 2 e 3 sono adattivi dichiarati, non holdout indipendenti. Non sono stati aggiunti ulteriori casi finanziari dall'auditor.", "",
        "## Cosa è stato ricostruito", "",
        f"- **{integer(summary['order_quantities_and_timestamps_checked'])} ordini**: quantità, prezzi, notionali, costi, disponibilità Open, ordine vendite/acquisti e associazione all'ultima istruzione maturata.",
        f"- **{integer(summary['independently_derived_instructions'])} istruzioni**, incluse **{integer(summary['independently_derived_reductions'])} riduzioni**: il revisore deriva anche l'assenza di istruzioni nei giorni senza trigger, non controlla soltanto gli ordini esistenti.",
        f"- **{integer(summary['independently_derived_raw_selection_targets'])} target mensili/iniziali**: ranking, opportunità, pesi e filtri ricostruiti dai dati; i target finali con controllo di volatilità sono verificati sullo stato di conto ricostruito.",
        "- **80 snapshot e 13.528 gruppi distinti**: idoneità storica, mediana del turnover a 63 sessioni includendo gli zeri, osservazione corrente, 126 rendimenti, Pearson, complete-link a 0,85, mediana dei punteggi e rappresentante più scambiato. Le 80 partizioni sono ricostruite in ciascuno dei tre blocchi.",
        "- **11 baseline disponibili di OLC108** identiche nei file finanziari e nei vettori decisionali. Mancano nell'archivio precedente solo i 4 stress passivi; non sono classificati come confronti superati.",
        f"- **{summary['unique_source_liquidity_instruments_checked']} ISIN** e **{integer(summary['source_liquidity_unique_rows_checked'])} righe uniche**: raw Close × Volume ricostruito esattamente dalle copie sorgente, con maschera V3 e verifica degli hash. Il campione comprende tutti i nomi selezionati nei target e 48 nomi deterministici di controllo per blocco.", "",
        "Il revisore contabile e quello dei segnali non importano engine, core o selettori di produzione. Il clustering usa la stessa libreria standard SciPy per il complete-link, con una matrice Pearson ricostruita separatamente; questa dipendenza comune è esplicita.", "",
        "## Riconciliazione", "",
        "| Controllo | Peggiore differenza assoluta |", "|---|---:|",
        f"| NAV o cassa | EUR {summary['max_nav_cash_error']:.3g} |",
        f"| Costo di un ordine | EUR {summary['max_per_order_cost_error']:.3g} |",
        f"| Identità giornaliera P&L meno costi | EUR {summary['max_daily_pnl_attribution_error']:.3g} |", "",
        "CAGR, valore finale, drawdown Close e Open/Close campionato, Calmar, volatilità, peggiori 21 sessioni, costi, giorni operativi, esposizione media e rendimenti annuali sono riconciliati. Le vendite e gli acquisti seguono il budget alla ricchezza Open precedente ai costi, la banda del 3%, il ticket e la scala comune di acquisto necessaria all'autofinanziamento. Nessun riempimento è ammesso senza Open valido.", "",
        "## Test negativi e causalità", "",
        "I sei controlli negativi sono stati respinti: quantità errata anche con cassa/NAV coerenti, commissione alterata, target cambiato senza cambiare ordini, esecuzione prima della maturazione, ritardo accorciato e identificativo di un'istruzione superata. Il conto originale non alterato è accettato.", "",
        "Tre date reali — 28 febbraio 2020, 30 dicembre 2022, 30 dicembre 2024 — sono confrontate con il solo prefisso storico e con 21 sessioni future alterate pesantemente in prezzi, volume e maschere. Tutte le 40 configurazioni mantengono gli stessi 120 vettori target, gruppi e correlazioni precedenti. È un controllo comportamentale separato che importa intenzionalmente i selettori di produzione.", "",
        "Per il blocco 3, si ricostruiscono separatamente i portafogli a 63/126/252 sessioni e i loro pesi di capitale. TILT conserva esattamente unione dei titoli ed esposizione del MIX; il revisore verifica anche la condizione dei tre sleeve pieni, la positività di momentum/accelerazione, il bonus diviso nelle parità e il cap target di 1/3 per gruppo e per coppia correlata sopra 0,85. La correlazione 0,85 è un filtro dentro ogni sleeve; la miscela può contenere una coppia più correlata se il peso totale della coppia resta entro 1/3. I TOP1 intenzionalmente investono fino al 100% in un solo ETF.", "",
        "## Aggregazione e bootstrap indipendenti", "",
        "Una verifica separata ricostruisce 16.000 rendimenti mensili e 1.400 rendimenti annuali dai DAILY, inclusi tutti i 200 risultati dell'anno 2024. Riproduce 16 confronti accoppiati e 112 contributi relativi annuali. La massima differenza sui log-rendimenti mensili è 2,54e-15; sui rendimenti annuali è zero.", "",
        "Il bootstrap usa blocchi mobili circolari di 6 mesi, 10.000 repliche e seed 109 sulle differenze mensili accoppiate. Il revisore ricostruisce le repliche tramite molteplicità dei mesi. Gli intervalli descrivono la media annualizzata dei log-rendimenti relativi, non la differenza dei CAGR in punti percentuali. Tutti i 16 intervalli descrittivi al 95% includono zero; non sono corretti per le prove multiple e non convalidano come holdout le scelte adattive.", "",
        "DEDUP_DUAL_TREND_OPP rispetto a DUAL21 migliora il CAGR storico di 3,3775 punti percentuali; la stima del rendimento log-relativo annualizzato è 0,027215, con intervallo descrittivo [−0,105784; +0,154132]. TILT rispetto a MIX migliora il CAGR di 0,6853 punti, con intervallo log-relativo [−0,016589; +0,034709]. MIX rispetto a HORIZON252 cambia insieme orizzonti e composizione: il confronto non isola un effetto puro della diversificazione.", "",
        "Le annualità BASE di DEDUP_DUAL_TREND_OPP e DUAL21 sono rispettivamente +33,9452% e −4,8925% nel 2024; +57,1652% e +46,2702% nel 2025; −15,2983% e −17,7022% nel 2026 fino al 30 ottobre. Le verifiche e tutti i confronti sono in `BOOTSTRAP_ANALYSIS_REVIEW.json`.", "",
        "## Confronto del filtro a parità di stato contabile", "",
        "La diagnosi del filtro di trend è verificata su 160 intervalli, 80 BASE e 80 LAG2. Per ogni intervallo, entrambi i rami ripartono dalle unità e dalla cassa effettive di TREND_OPP alla chiusura del segnale. Un ramo mantiene il target effettivo e l'altro rimuove soltanto il filtro aggiuntivo sugli emergenti. I controfattuali non vengono concatenati e non aggiungono nuove strategie complete ai 200 percorsi.", "",
        "Il revisore riproduce indipendentemente tutti i 320 rami con la propria funzione di dimensionamento degli ordini e i target già verificati, senza importare il simulatore di produzione. La massima differenza di NAV terminale è EUR 7,28e-12, quella dei costi EUR 2,84e-14. I 160 terminali del ramo effettivo coincidono esattamente con i DAILY originali. La maturazione k+1+lag, gli Open validi, i riempimenti parziali e la chiusura alla decisione successiva sono rispettati. Non si osservano riempimenti comuni anteriori alla nuova maturazione; quel ramo resta controllato per lettura del metodo, senza una ricorrenza empirica in questi intervalli.", "",
        "In ciascuno scenario cambiano 40 target su 80. Nei 40 casi cambiati, BASE presenta 24 vantaggi e 16 svantaggi, media +87,2645 bp e mediana +176,0804 bp; LAG2 presenta 27 vantaggi e 13 svantaggi, media +90,1865 bp e mediana +59,9171 bp. Su tutti gli 80 intervalli, inclusi i 40 pareggi, le medie sono +43,6322 bp e +45,0933 bp e la mediana è zero in entrambi gli scenari. Un vantaggio significa rendimento maggiore del ramo senza filtro, anche se entrambi perdono: non è un conteggio di trade profittevoli.", "",
        "Tutte le differenze usano lo stesso NAV iniziale effettivo come denominatore. Media e mediana non sono CAGR, contributi annuali additivi o risultati di una nuova strategia composta. Il candidato e la diagnosi sono stati scelti dopo i risultati; l'esito resta descrittivo. Evidenza completa: `MATCHED_STATE_REVIEW.json`.", "",
        "## Precisione numerica del revisore", "",
        f"La lettura CSV usa `float_precision='round_trip'`. Un test documenta perché il parser predefinito perde un residuo di 1,82e-12 unità il 12 dicembre 2022 e ricostruisce zero sessioni differite anziché una. Con la lettura esatta si riconcilia il contatore senza modificare alcun risultato finanziario. Il conteggio delle sessioni differite dovute solo a residui numerici nei 200 conti è **{summary['numerical_residue_only_deferred_sessions']}**. La soglia di posizione economica resta 1e-10 unità. Vedere `AUDITOR_PRECISION_NOTE.md` e `CSV_PRECISION_REGRESSION.json`.", "",
        "## Limiti pratici emersi", "",
        f"Tra tutti gli scenari, **{integer(p_all['above_ten_percent'])}/{integer(p_all['orders'])} ordini** superano il 10% del controvalore giornaliero registrato; **{integer(p_all['above_full_daily_turnover'])}** superano l'intero controvalore. Nei soli casi BASE sono rispettivamente **{integer(p_base['above_ten_percent'])}/{integer(p_base['orders'])}** e **{integer(p_base['above_full_daily_turnover'])}**. I percorsi/scenari non sono osservazioni indipendenti e questi conteggi non sono frequenze prospettiche.", "",
        f"Il rapporto massimo è **{p_all['maximum_ratio']:.2f}×**: `{primary.path_id}`, {primary.date}, {primary.ticker}, ordine EUR {money(primary.notional)} rispetto a EUR {money(primary.raw_traded_eur)} registrati. La mediana del turnover a 63 sessioni non vincola il volume del giorno di esecuzione. Il volume di una singola sede può non rappresentare la liquidità totale dell'ETF, ma queste osservazioni impediscono di certificare l'ipotesi di riempimento all'Open con impatto fisso di 15 bp. Nessun denominatore di turnover degli ordini è nullo.", "",
        f"L'audit descrittivo copre tutti i {integer(sum(s['closing_states'] for s in price_age['stages']))} stati di chiusura, inclusa l'ultima sessione, e {integer(sum(s['held_marks'] for s in price_age['stages']))} marcature di posizioni. L'età massima di un Close detenuto è {max(s['maximum_age_calendar_days'] for s in price_age['stages'])} giorni di calendario; le sessioni di conto con età superiore a 5 giorni sono {sum(s['held_sessions_with_age_over5'] for s in price_age['stages'])}. Ciò non certifica la negoziabilità contemporanea.", "",
        "Le guardie TREND_REDUCE sono effettivamente sell-only. Poiché congelano anche il peso delle posizioni superstiti e l'esecuzione forzata supera la banda del 3%, possono vendere una piccola parte di un titolo superstite se il suo peso relativo sale tra segnale ed esecuzione. Non equivale a vendere esclusivamente i nomi che hanno attivato l'uscita.", "",
        "Restano i limiti già dichiarati: catalogo attuale e survivorship; maschera Open che usa retrospettivamente il volume positivo della giornata completata; vintage dei fattori di aggiustamento non certificato; interesse sulla cassa nullo; imposte escluse; unità economiche frazionarie; drawdown campionato Open/Close. Nessuna verifica rende questi dati un universo storico perfettamente point-in-time o converte un test adattivo in una conferma fuori campione.", "",
        "## Riproduzione", "", "```bash",
        "python validation/run_independent_audit.py",
        "python validation/run_independent_audit.py --results-directory results_stage2 --output-directory validation/stage2",
        "python validation/run_independent_audit.py --results-directory results_stage3 --output-directory validation/stage3",
        "python validation/check_tamper_rejections.py",
        "python validation/check_csv_precision_regression.py",
        "python validation/check_prefix_causality.py",
        "python validation/check_held_price_age.py",
        "python validation/check_analysis_bootstrap.py",
        "python validation/check_matched_state_review.py",
        "python validation/build_audit_report.py", "```", "",
        "Fonti primarie dell'audit: `INDEPENDENT_QA.json`, `stage2/INDEPENDENT_QA.json`, `stage3/INDEPENDENT_QA.json`, le rispettive `INDEPENDENT_RECONSTRUCTIONS.csv`, `INDEPENDENT_GROUP_CONDITIONS.csv.gz`, `LIQUIDITY_SOURCE_CHECKS.csv`, `TRADE_PARTICIPATION.csv.gz`, `HELD_PRICE_AGE_ALL_CLOSES.csv`, `BASELINE_REPLICATION.csv`, `PREFIX_CAUSALITY.json`, `TAMPER_CONTROLS.json`, `CSV_PRECISION_REGRESSION.json` e i tre manifest di esecuzione."
    ]
    (output / "INDEPENDENT_REVIEW_IT.md").write_text("\n".join(lines) + "\n")
    hashes = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(output.glob("*.py"))}
    (output / "VALIDATION_CODE_HASHES.json").write_text(json.dumps(hashes, indent=2) + "\n")
    print(json.dumps({key: value for key, value in summary.items() if key != "stages"}, indent=2))


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[1])
