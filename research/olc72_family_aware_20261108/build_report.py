#!/usr/bin/env python3
"""Render OLC72 report from verified CSVs only; emit hash manifest and distributable ZIP."""
from pathlib import Path
import pandas as pd,numpy as np,hashlib,zipfile,json,datetime
R=Path(__file__).parent;O=R/'results';U=pd.read_csv(O/'OLC72_SUMMARY.csv');A=pd.read_csv(O/'OLC72_ANNUAL.csv');B=pd.read_csv(O/'OLC72_BOOTSTRAP.csv');C=pd.read_csv(O/'OLC72_CONDITIONAL_FAMILY_SUMMARY.csv');D=pd.read_csv(O/'OLC72_CONDITIONAL_PAIRED_CI.csv');M=pd.read_csv(O/'OLC72_MODEL_USAGE.csv');K=pd.read_csv(O/'OLC72_DECISION_CHANGES.csv')
F=lambda v:f'{v:+.2f}'
def rows(yr):
 lines=['| Mercato | Anno | Originale 21d | Family-aware 21d | Δ pp | Originale 42d | Family-aware 42d |','|---|---:|---:|---:|---:|---:|---:|']
 for market in ('EU','USA'):
  for year in yr:
   x=A[(A.market==market)&(A.year==year)].set_index('method')
   o=x.loc['ORIGINAL_FUSION'];t=x.loc['FAMILY_FUSION']
   lines.append(f'| {market} | {year} | {o.ret21:.2f}% | {t.ret21:.2f}% | {F(t.ret21-o.ret21)} | {o.ret42:.2f}% | {t.ret42:.2f}% |')
 return '\n'.join(lines)
def fmtc():
 l=['| Mercato | Famiglia | Δ originale−matched, pp | IC 95% a blocchi, pp |','|---|---|---:|---:|']
 for _,d in D.iterrows():
  l.append(f'| {d.market} | `{d.family}` | {d.mean_delta_original_minus_matched21_pp:+.3f} | [{d.ci95_low:+.3f}; {d.ci95_high:+.3f}] |')
 return '\n'.join(l)
main=U[U.period=='MAIN_2021_2024'];late=U[U.period=='LATE_2025'];q=B[B.metric=='p21']
md='''# OLC72 — Test nativo Return125 *family-aware*, controllo USA ed importanza condizionale approssimata

**8 novembre 2026 · Stato: COMPLETO, CONTROLLI PASSATI, NESSUNA PROMOZIONE**  
Periodi 2019–2026 già ampiamente esplorati: tutti i risultati sono retrospettivi, non prove di alpha fuori campione. OLC19, OLC67 e `main` non modificati.

## Risposta sintetica

L'ipotesi di aumentare la qualità economica del ramo Return125 **senza aggiungere feature o cambiare la FUSION**, ma equilibrando le probabilità di campionamento XGBoost delle 46 famiglie economiche, è stata testata su entrambi i mercati con la ricetta nativa originale e **30 refit annuali** (2021–25, tre seed per mercato/anno). La FUSION originale resta superiore sul MAIN 2021–24. In 2025 il candidato è migliore staticamente, ma quell'anno è già esplorato, e la conclusione non è stabile per tutti gli anni precedenti. Nessun nuovo CAGR viene dichiarato: non è stato autorizzato un replay OLC19 poiché il gate di qualità Top2 è fallito.

## 1. Recupero dei modelli nativi USA e riproducibilità

I modelli USA **originali** si trovano in `parents/fits/USA/BASE/{year}/RETURN_{seed}.ubj` nei due volumi del checkpoint OLC08F; i modelli EU in `fits/EU/R_RSI_DOMAIN/{year}/RETURN_{seed}.ubj` nel pacchetto RSI. Abbiamo verificato che i due insiemi riproducono esattamente `RETURN` e `FUSION` OLC19 su **120 market-month**, 60 per ciascun mercato, per 2021–25. Su **18.216 righe originali** la parità degli score Return è esatta.

In aggiunta, un refit **senza nessuna modifica** di un modello originale seed101 nel 2024, effettuato riproducendo gli input X, XP, le etichette, i gruppi e l'intera ricetta nativa, ha dato **errore massimo prediction = 0.0** sia EU sia USA. Questo rende attribuibile l'esperimento successivo all'unico intervento di campionamento. È stato recuperato il codice storico: non utilizzare la configurazione mostrata da un Booster UBJ *ricaricato* per inferire gli iperparametri di training, perché il caricamento reimposta diversi parametri di training ai default.

### Parametri rimasti immutati

Return XGB `rank:ndcg` con relevance 0..15 costruita per ogni mese con la differenza economica normalizzata `(r - mediana)/(q90 - q10)` e clipping, labels disponibili solo dopo `exit_date_21`, `ndcg_exp_gain=False`, pair method `topk` con 5 coppie, 360 round, max_depth=4, eta=.035, subsample=.85, colsample_bytree=.8, min_child_weight=8, lambda=8, alpha=.1, seed 101/202/303. Tutti i 125 input restano identici, compresi NaN e ordine. Le altre previsioni ET/XGB Hybrid42, memoria e FUSION 0.475/0.525 sono congelate.

**Unica modifica:** in XGBoost DMatrix, per la feature j appartenente alla famiglia f con `k_f` colonne di tipo RAW/PCT/DEV si imposta `feature_weights[j]=1/k_f`, in modo che ciascuna delle 46 famiglie abbia la stessa massa *attesa* nel campionamento dell'80% delle feature per albero. La procedura non costringe il modello a usare le famiglie in modo uniforme: può legittimamente sceglierne alcune più spesso o con gain maggiore.

## 2. Rendimento futuro Top2, test principale 2021–24

| Mercato | FUSION originale 21d | Family-aware 21d | Δ 21d pp | Orig. 42d | Family-aware 42d | Persistenza Orig. → Family |
|---|---:|---:|---:|---:|---:|---:|
'''
for market in ['EU','USA']:
 x=main[main.market==market].set_index('method');o=x.loc['ORIGINAL_FUSION'];t=x.loc['FAMILY_FUSION']
 md+=f'| {market} | {o.p21_pct:.3f}% | {t.p21_pct:.3f}% | {t.p21_pct-o.p21_pct:+.3f} | {o.p42_pct:.3f}% | {t.p42_pct:.3f}% | {o.persistent_rate:.1%} → {t.persistent_rate:.1%} |\n'
md+='''
**Esito:** fallisce il criterio predefinito di miglioramento Top2 contemporaneo in EU e USA. A 21 sedute, la differenza in EU è -0,190 pp, USA -0,634 pp. Le CI descrittive bootstrap a blocchi sei mesi includono zero per il vantaggio di rendimento, ma il segno medio sfavorevole in entrambi i mercati è sufficiente per respingere il gate preregistrato; la MSE della futura forza relativa non è stata addestrata nuovamente, perché l'obiettivo è il ranking nativo.

## 3. Anni singoli, inclusi 2024 e 2025

'''
md+=rows((2021,2022,2023,2024,2025))
md+='''

Il 2024 è importante: il candidato peggiora il Top2 a 21 sedute in entrambi i mercati. Nel 2025 si osserva un'inversione favorevole, EU 1.50%→2.29%, USA 2.00%→3.44%, ma questo **non è** un holdout mai esaminato. Le previsioni 2025 sono cronologiche, però la scelta dell'ipotesi e decine di esperimenti precedenti hanno già utilizzato lo stesso periodo. Nessuna selection policy 2026 o rendimento 2026 è simulato da OLC72.

## 4. Bilanciamento della massa di campionamento ≠ bilanciamento delle importanze economiche

'''
for market in ['EU','USA']:
 x=M[(M.market==market)&M.year.between(2021,2024)].groupby('variant')[['effective_families_HHI','top5_family_gain_share','n_families_used']].mean()
 md+=f'- **{market}:** concentrazione del gain delle cinque famiglie principali: {x.loc["ORIGINAL","top5_family_gain_share"]:.1%} originale contro {x.loc["FAMILY_BALANCED","top5_family_gain_share"]:.1%} candidate; numero efficace per HHI {x.loc["ORIGINAL","effective_families_HHI"]:.1f} → {x.loc["FAMILY_BALANCED","effective_families_HHI"]:.1f}. Tutte e 46 le famiglie presentano gain positivo nei modelli originali e nuovi.\n'
md+='''
Questo dimostra che la ridondanza **non si risolve semplicemente equalizzando la probabilità d'accesso agli alberi**. In EU, dopo il campionamento bilanciato, il gain appreso risulta anzi più concentrato. `total_gain` degli split non è importanza causale né garanzia di generalizzazione.

La variante cambia la coppia Top2 nel 2021–24 in 25/48 mesi EU e 30/48 mesi USA: l'intervento non è cosmetico, ma non porta un miglioramento economico stabile.

## 5. Test originale nativo USA + perturbazioni condizionali abbinate

OLC71D aveva perturbato indipendentemente dalle altre feature, per famiglia, modelli originali europei. OLC72 usa i modelli **originali EU e USA** e modifica RAW/PCT/DEV congiuntamente, scegliendo per ogni ETF uno dei cinque donatori più vicini **nella stessa data** rispetto alle altre 45 famiglie RAW (ordinamenti normalizzati per data, missing median-neutral soltanto per il matching; il modello riceve i valori originali del donatore). Due seed fissi; sei famiglie già emerse in OLC71, non scelte sulla base degli outcome di OLC72. 6 famiglie × 2 repliche × 12 mesi × 5 anni × 2 mercati = **1.440** valutazioni mensili. Il bootstrap ricampiona i **48 mesi**, mai le 96 repliche come se fossero indipendenti.

La procedura riduce distorsioni di un cambio arbitrario delle rappresentazioni ma NON è un vero conditional-knockoff generativo: possono comunque essere introdotti vettori fuori distribuzione. La differenza tra rendimento Top2 originale e matching **non è un contributo causale**.

### Differenziale Top2 21 sedute originale meno matching (2021–24)

'''
md+=fmtc()
md+='''

**Tutte le CI al 95% contengono zero.** Alcuni risultati di OLC71D in EU si ridimensionano quando si rispetta la somiglianza con il resto delle feature, es. `acc_mom_21_63` da +0,45 a circa +0,20 pp; per altre famiglie il segno cambia. Non esiste un insieme di famiglie emerso con importanza condizionale positiva e stabile e replicata in EU/USA. Le sei famiglie erano state selezionate alla luce degli esiti EU OLC71D, quindi non sono ipotesi indipendenti.

## 6. Decisione e ricerca successiva

- Nessuna nuova strategia promossa. **OLC19** resta baseline operativa congelata; **OLC67** resta un candidato di ricerca da verificare prospetticamente.
- Dalle 125 feature provengono segnali realmente usati, ma un equalizzatore semplice del campionamento non dimostra rendimento incrementale robusto. È invece plausibile che alcune **interazioni fra famiglie** e la loro **validità temporale** siano la parte delicata della generalizzazione.
- Per ulteriori esperimenti, prima di aggiungere un learner, verificare quali interazioni *tra famiglie* conservano valore predittivo su finestre non utilizzate dalla ricerca e con distanze temporali; ma lo storico 2019–26 è già stato fortemente esplorato, quindi il risultato resterebbe esplorativo.
- Se la variante non supera la gate sul Top2, non si deve calcolare un CAGR inventato: servirebbe il vero replay `TOP2_CONTEXT_REVALUE → V6 → FAST_LOCK3` con costi e stato di rischio, eseguibile soltanto dopo aver superato il filtro.
- Dati OHLC non ricertificati per adjustment/total return, universe point-in-time e delisting, originale maschera osservazioni USA, bid/ask/stop reali; riproducibilità computazionale non equivale a operatività verificata.

## 7. Riproducibilità e controllo indipendente

- Hash delle cinque sorgenti immutabili controllati contro protocollo.
- 120 market-month e 18.216 righe Return/FUSION originali riprodotte esattamente per 2021–25, entrambi i mercati.
- 2024 native XGBoost seed101 riaddestrato senza modifica: **zero differenze** dall'originale USA e EU.
- 30 nuovi booster family-aware salvati, ricaricati per controlli indipendenti su 2021/2024/2025, 240 coppie Top2 verificate e payoff confrontati con OLC72_MONTHLY.
- 1.440 perturbazioni abbinate, doppia verifica di Top2/changement e CI bootstrap a 48 eventi per mercato.
- Fonte: checkpoint OLC08F, RSI e OLC19 già nella Library; non sono duplicati nel nuovo ZIP da decine di MB.
- GitHub branch `research/olc72-return125-family-aware-20261108`, pre-registrazione prima dei 30 fit e delle perturbazioni, protocollo commit `3d9b9aef78cfaafa2d295270a4bf0ed6def0e153`.
'''
(R/'REPORT_OLC72_IT.md').write_text(md)
readme='''# OLC72 — 125 feature native XGBoost family-aware test

Research-only, November 8, 2026. No production or main changes. Outcomes 2021–2025 mined historically, not independent OOS. Sources from `/ETF_Research/OLC08_Ripristino_20261101/` and `/ETF_Research/OLC19_Rischio_Rientro_20261102/` must be materialized into `/mnt/data/etf_source` (or change `SRC` in scripts). The new zip contains code, 30 XGB UBJ family-weighted models, predictions, QA, report, **not** the parent multi-hundred-MB source data.

## Rerun

```
python verify_exact_native_recipe.py
python run_olc72.py
python verify_olc72.py
python conditional_family.py
python verify_conditional.py
python diagnose_family_usage.py
python build_report.py
```

`run_olc72.py` verifies source SHA256, original EU/USA Return/FUSION score parity, then refits 30 models under original objective/hyperparams with only DMatrix feature_weights changed (1 / count of raw/pct/dev siblings). `conditional_family.py` reuses the frozen original XGB model binaries in parent source volumes and runs approximate matched conditional family swap (six prespecified families, 2 reps). Summaries in `results/`. The baseline original Return/FUSION is only a *ranking signal*; it differs from OLC19 context and trading strategy. No CAGR or trading recommendation is produced by this work.

Methodological differences from OLC71: USA original native models recovered from split checkpoint; exact re-training QA both markets; original XGB `colsample_bytree=.8` and original native economic rank labels; full 125 features with 46 equal family sampling weights; two-seed matched family perturbation (approximate conditional), both markets.

Run reproducibility environment: Python 3.10+, numpy 2.3.5, pandas 2.2.3, xgboost 3.1.3. Change in XGBoost version may perturb numeric results or the exact model parity check; do not claim parity if environment differs.
'''
(R/'README.md').write_text(readme)
files=sorted([p for p in R.rglob('*') if p.is_file() and p.name not in {'parity_test.py'} and not ('__pycache__' in p.parts) and p.suffix not in {'.log','.pid'} and p.name not in {'exit_code','run.pid','conditional.pid'} and not p.name.startswith('OLC72_FULL_')])
h=[]
for f in files:
 h.append({'path':str(f.relative_to(R)),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
manifest={'report_date':'2026-11-08','status':'complete_failed_economic_gate_no_promotion','source_sha256':json.loads((O/'OLC72_QA.json').read_text())['source_hashes'],
 'artifact_count':len(h),'files':h,'github_branch':'research/olc72-return125-family-aware-20261108','git_preregister_commit':'3d9b9aef78cfaafa2d295270a4bf0ed6def0e153'}
(R/'MANIFEST.json').write_text(json.dumps(manifest,indent=2))
archive=R.parent/'OLC72_Return125_FamilyAware_20261108_VERIFICATO.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in files+[R/'MANIFEST.json']:
  z.write(f,arcname=str(f.relative_to(R)))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
print('REPORT:',R/'REPORT_OLC72_IT.md','characters',len(md))
print('ZIP:',archive,'bytes',archive.stat().st_size,'SHA256:',hashlib.sha256(archive.read_bytes()).hexdigest(),'files',len(files)+1)