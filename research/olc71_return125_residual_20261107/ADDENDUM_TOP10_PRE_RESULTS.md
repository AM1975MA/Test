# OLC71C — Test condizionale del valore Return125 nei Top10 già selezionati (registrato prima degli outcome top10)
**7 novembre 2026, diagnostic-only; OLC71A e OLC71B sono già noti.** La prova non usa date OOS indipendenti e non autorizza una promozione strategica o un nuovo CAGR.

### Problema
OLC65 ha identificato il ranking errato entro Top10 come principale differenziale teorico. Un risultato nullo su tutto il paniere in OLC71A non esclude che la natura degli errori sia concentrata nelle prime dieci posizioni.

### Input e confronto prespecificato
Stessi archivii, feature/labels, chiavi/as-of e coorti OLC71A. Per ogni market×date scegliere Top10 secondo `ORIGINAL_FUSION` originale, **prima** di osservare i rendimenti futuri. Un record ticker/evento nella shortlist; score disponibili, stessi date/entry/exit; no label future in selezione. Train expanding con gruppi `exit_date_63 < Jan1 fit`, 2019..anno precedente, solo shortlist originale. Target economico logbp futuro a21 sedute, centrato sulla mediana dei dieci candidati dello stesso mese (training ONLY after mature). Un fit annuo per mercato 2021..2025. Scala/preprocess del medesimo OLC71A: median imputer, StandardScaler fit-only, Ridge alpha=100.
Tre bracci fissi: `TOP10_SCORE_RIDGE` su RETURN/ORIGINAL_CURRENT/ORIGINAL_SMOOTH; `TOP10_PCT46_RIDGE` con le medesime tre più i 46 percentili di Return125; `TOP10_FULL125_RIDGE` con le medesime tre più tutte le 125. Classificare direttamente i due migliori dei Top10 secondo score previsti. Riferimento `ORIG_FUSION_TOP2` dalla FUSION senza refit. Nessun aggiustamento dopo l'esito.

### Metriche
48 mesi per mercato 2021–24, 2025 separato, payout medio statico Top2 21/42 sedute e MSE nel Top10, Correlazione Spearman nel Top10, presenza Top2 nel quintile superiore di tutto il mercato, quota Top2 negativa. Preferire bassa MSE e Top2 migliore contro score-control e FUSION in entrambi i mercati; se nessuna pass, stop. Nessun CAGR completo possibile senza replay contestualizzazione/V6/FAST_LOCK3. Rischi point-in-time/mancanza USA mask rimangono.
