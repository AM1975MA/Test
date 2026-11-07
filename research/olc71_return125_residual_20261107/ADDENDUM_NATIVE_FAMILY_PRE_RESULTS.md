# OLC71D — Diagnostica native-family permutation sul ramo originale Return125

**7 novembre 2026 — dichiarato DOPO OLC71A/B/C, PRIMA di calcolare OLC71D.** Esplorazione, NON prova indipendente; dati storici 2019–2026 ampiamente studiati. Non modifica OLC19, OLC67 o main.

## Ipotesi
Nei modelli XGBoost Return originali, le famiglie RAW/PCT/DEV dello stesso segnale possono influire sul ranking come blocco correlato. I gain degli split non indicano se il blocco contenga informazione economicamente utile oltre ai restanti 45 blocchi.

## Input vincolati
- I 24 modelli autentici Return EU XGBoost (3 seed × anni 2019–2026) nell'archivio `OLC08_03_RSI_Confronto_Verificato_20261101.zip` e gli input EU RSI corretti in `OLC08F_01_FeaturePack_20261101.zip`.
- Verificare prima di ogni perturbazione, per anno 2021–2025, la parità del ranking Return nativo con gli score archiviati OLC19 su tutti i ticker e mesi (pareggi inclusi). Se fallisce, STOP.
- Per ricostruire FUSION usare **solo** `0.475*RETURN + 0.525*ORIGINAL_SMOOTH` con ramo SMOOTH originale invariato, non stimare nuovi pesi o percentili di FUSION. Nessun layer contestuale, V6 o rischio è simulato.

## Esperimento fissato
- Gruppi: 46 indicatori economici di base; per ciascuno permutare CONGIUNTAMENTE tutte le rappresentazioni presenti RAW/PCT/DEV per gli ETF di **una stessa data**, preservando distribuzioni, dipendenze dentro il blocco e maschera NaN; permettere che il blocco perturbato sia incoerente con altri indicatori, caveat di off-manifold.
- Due repliche predefinite 71101 e 71102, permutation key SHA256(seed|anno|data|famiglia), indipendente dall'ordine delle righe.
- Re-inferenza XGBoost esattamente sugli originali modelli annuali 2021–2025 (nessun training). Media dei tre seed originali e rank percentile per data prima di FUSION. Valutare 2021–24 MAIN, 2025 LATE separato, su mesi con due future label validi e medesimo supporto di OLC71.
- Misure con e senza outcome: % di date con FUSION Top2 cambiato, spostamento medio |score Return| e Top2 fwd 21d medio. `original - permuted` positivo = valore attribuito *dal perturbation test* al blocco; non è un effetto causalmente identificato né la sua informazione originale non sfruttata.
- Controlli: tutti 46 gruppi, senza filtrare in base ai risultati; ricostruzione del ranking originale da modelli salvati entro float32 e parità esatta delle posizioni Top2 sui mesi valutati. Mantenere l'originale come unico reference.

## Soglia di interpretazione
Nessuna decisione di rimuovere o promuovere blocchi da questo test ex post. La domanda è diagnosi del modello, non selezione della migliore ablation dopo aver visto i rendimenti. Modelli USA UBJ non presenti negli archivi recuperati, quindi **nessun risultato Usa può essere attribuito a questo controllo**.