#!/usr/bin/env python3
"""Generate OLC102 retrospective source-backed report and figures from locked result files."""
from pathlib import Path
import json,hashlib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path('/mnt/data/olc102');OUT=R/'results'
s=pd.read_csv(OUT/'OLC102_SCORECARD.csv')
p=pd.read_csv(OUT/'OLC102_PAIRED_BLOCK6.csv')
c=pd.read_csv(OUT/'OLC102_SELECTION_SUMMARY.csv')
d=pd.read_csv(OUT/'OLC102_DAILY.csv.gz',parse_dates=['date'])
qa=json.loads((OUT/'OLC102_NATIVE_QA.json').read_text());assert qa['n_paths']==len(s)==76
assert len(s[(s.market=='EU')&(s.fee==.001)])==len(s[(s.market=='USA')&(s.fee==.001)])==19

arms=['OLC19_IMMEDIATE','OLC67_MINVAR63_DELAY3','OLC19_NATIVE_DELAY3','FIXED_DAY2_HALF','FIXED_DAY2_MINVAR63','ML_DAY1_HALF','ML_DAY2_HALF','ML_AVG_80_15_05_HALF','ML_AVG_50_30_20_HALF','ML_AVG_20_30_50_HALF','ML_SCORE_AVG_50_30_20_HALF','ML_AVG_80_15_05_MINVAR63','ML_AVG_50_30_20_MINVAR63','ML_AVG_20_30_50_MINVAR63']
labels={'OLC19_IMMEDIATE':'OLC19 originale · immediato / 50-50','OLC67_MINVAR63_DELAY3':'OLC67 · MINVAR63 / DELAY3','OLC19_NATIVE_DELAY3':'OLC19 · 50-50 / DELAY3 nativo','FIXED_DAY2_HALF':'Top2 originale · terza apertura / 50-50','FIXED_DAY2_MINVAR63':'Top2 originale · terza apertura / MINVAR63','ML_DAY1_HALF':'ML della prima chiusura aggiuntiva / 50-50','ML_DAY2_HALF':'ML della seconda chiusura aggiuntiva / 50-50','ML_AVG_80_15_05_HALF':'ML media 80/15/05 / 50-50','ML_AVG_50_30_20_HALF':'ML media 50/30/20 / 50-50','ML_AVG_20_30_50_HALF':'ML media 20/30/50 / 50-50','ML_SCORE_AVG_50_30_20_HALF':'Media degli score 50/30/20 / 50-50','ML_AVG_80_15_05_MINVAR63':'ML media 80/15/05 / MINVAR63','ML_AVG_50_30_20_MINVAR63':'ML media 50/30/20 / MINVAR63','ML_AVG_20_30_50_MINVAR63':'ML media 20/30/50 / MINVAR63'}

def fmt(v):return ('+' if v>0 else '')+f'{v*100:,.2f}%'.replace(',','.')
def cell(arm,market,col='CAGR_FULL',fee=.001):
 g=s[(s.market==market)&(s.arm==arm)&(s.fee==fee)];assert len(g)==1,(market,arm,fee)
 return float(g[col].iloc[0])

ret=[]
for arm in arms: ret.append(f"| {labels[arm]} | {fmt(cell(arm,'EU'))} | {fmt(cell(arm,'USA'))} | {fmt(cell(arm,'EU','MaxDD_FULL'))} | {fmt(cell(arm,'USA','MaxDD_FULL'))} |")
stress=[]
for arm in ['OLC19_IMMEDIATE','OLC67_MINVAR63_DELAY3','FIXED_DAY2_HALF','ML_AVG_80_15_05_HALF','ML_AVG_50_30_20_HALF','ML_AVG_50_30_20_MINVAR63']:
 stress.append(f"| {labels[arm]} | {fmt(cell(arm,'EU',fee=.003))} | {fmt(cell(arm,'USA',fee=.003))} |")

stat=[]
for a,b in [('ML_AVG_50_30_20_HALF','FIXED_DAY2_HALF'),('ML_AVG_80_15_05_HALF','FIXED_DAY2_HALF'),('ML_AVG_20_30_50_HALF','FIXED_DAY2_HALF'),('ML_AVG_50_30_20_MINVAR63','FIXED_DAY2_MINVAR63')]:
 ar=[]
 for m in ('EU','USA'):
  row=p[(p.market==m)&(p.arm==a)&(p.control==b)].iloc[0]
  ar.append(f"{row.delta_log_annual*100:+.2f} [{row.ci95_low*100:+.2f}; {row.ci95_high*100:+.2f}]")
 stat.append(f"| {labels[a]} | {ar[0]} | {ar[1]} |")

# One chart per market, no manual colors; same series and legend to compare.
for m in ('EU','USA'):
 fig,ax=plt.subplots(figsize=(11,5))
 subset=d[(d.market==m)&(d.fee==.001)].sort_values('date')
 for arm in ['OLC19_IMMEDIATE','OLC67_MINVAR63_DELAY3','FIXED_DAY2_HALF','ML_AVG_80_15_05_HALF','ML_AVG_50_30_20_HALF']:
  x=subset[subset.arm==arm]; y=x.nav.to_numpy(float); y=y/y[0]
  ax.plot(x.date.to_numpy(),y,label=labels[arm],linewidth=1.4)
 ax.set(title=f'OLC102 — NAV normalizzata · {m} · retrospettiva',ylabel='NAV (base 1)',xlabel='Data di valutazione');ax.grid(True,alpha=.22)
 ax.legend(fontsize=8,loc='upper left',frameon=False);fig.tight_layout();fig.savefig(OUT/f'OLC102_NAV_{m}.png',dpi=155);plt.close(fig)

sel=[]
for key in ('ML_DAY1','ML_DAY2','ML_AVG_80_15_05','ML_AVG_50_30_20','ML_AVG_20_30_50','ML_SCORE_AVG_50_30_20'):
 eu=int(c[(c.market=='EU')&(c.policy==key)].changed_pairs.iloc[0]);us=int(c[(c.market=='USA')&(c.policy==key)].changed_pairs.iloc[0]);sel.append(f'| {key} | {eu}/90 | {us}/90 |')

report=f'''# OLC102 — Ricalcolo giornaliero dei veri rank ML e medie ponderate\n\n**13 novembre 2026 · Revisione retrospettiva; nessuna promozione operativa.**\n\n## 1. Conclusione\n\nSono state ricostruite le 125 feature Return e 42 feature Hybrid con le formule originali alle 90 chiusure mensili e alle successive una/due chiusure. Sono stati richiamati i modelli annuali ET/XGB, Return125 e OLC14 già addestrati e congelati; **nessun refit su outcome nuovi**. Per isolare le differenze nella popolazione dei percentili, i cambiamenti di score dei modelli dal giorno iniziale sono applicati agli score mensili canonici OLC19, senza alterare l'ordinamento storico al giorno di segnale.\n\nIl test completo con V6 e FAST_LOCK3 comprende **76 replay nativi** (19 bracci × 2 mercati × 2 ipotesi di costi). **Nessuna delle medie ponderate testate supera il Top2 originale a timing identico in entrambi i mercati.** Il candidato di ricerca OLC67 rimane congelato e non viene sostituito.\n\n## 2. Risultati economici comparabili\n\nPer ogni media su tre chiusure il confronto valido è **FIXED_DAY2**, stesso ingresso alla terza apertura; cambiano solo i due ETF, non timing, V6 e protezione. Le formule dei pesi si riferiscono al rango percentile (non al rendimento):\n\n`S_t = w0 * rank(ML_CLOSE0) + w1 * rank(ML_CLOSE1) + w2 * rank(ML_CLOSE2)`\n\nL'azione è ammissibile soltanto all'apertura dopo la chiusura utilizzata. La politica `ML_SCORE_AVG` media invece direttamente gli score contestuali.\n\n**FULL** dalla prima apertura febbraio 2019 all'apertura del 1º luglio 2026; CAGR annualizzato a 252 sedute secondo il motore OLC19, costi nominali legacy `fee=0.001`, `stop_friction=0.001`. Non sono prezzi/slippage di un broker certificato.\n\n| Architettura | CAGR EU | CAGR USA | MaxDD EU | MaxDD USA |\n|---|---:|---:|---:|---:|\n{chr(10).join(ret)}\n\nLa media **50/30/20** con pesi 50/50 scende da **22,19% a 16,17% EU** e da **42,81% a 33,53% USA** contro FIXED_DAY2 (−6,02 e −9,28 punti CAGR). Il drawdown UE peggiora da −28,65% a −36,04%. Il peso MINVAR63 non salva la media: 15,60% EU e 27,34% USA.\n\nLa media **80/15/05** è più conservativa ma non domina: 17,82% EU e 38,28% USA contro lo stesso Top2 congelato con timing fisso. La media **20/30/50**, più sensibile agli ultimi ranghi, recupera quasi la baseline in EU (21,86%), ma perde molto in USA (22,50%). Non è lecito scegliere per mercato il peso vincitore ex post.\n\n![OLC102 NAV Europea](results/OLC102_NAV_EU.png)\n![OLC102 NAV USA](results/OLC102_NAV_USA.png)\n\n## 3. Qual è la frequenza di cambiamento dei Top2?\n\nI rank giornalieri effettivi comportano rotazioni rilevanti anche quando il modello originale è invariato:\n\n| Politica | EU Top2 diversi | USA Top2 diversi |\n|---|---:|---:|\n{chr(10).join(sel)}\n\nL'80/15/05 limita i cambi a 17/90 UE e 14/90 USA, ma non produce un miglioramento economico. Il problema quindi non è soltanto il numero di sostituzioni: conta la qualità dei cambiamenti e il loro percorso di rischio. Il riordino giornaliero può penalizzare la selezione mensile originale senza che la stabilità visiva del ranking ne evidenzi immediatamente il costo.\n\n## 4. Incremento al medesimo timing e incertezza\n\nIntervalli **descrittivi** al 95% su differenza di **log-rendimento annualizzato** (non differenza di CAGR), 5000 bootstrap circolari appaiati a blocchi di sei mesi, seed 102113. Lo storico è stato ripetutamente studiato da OLC01–102; non sono corretti per selezione/multipli test. I due mercati non sono prove indipendenti.\n\n| Contrasto rispetto al Top2 originale alla terza apertura | Δ log annuo EU in pp [IC95%] | Δ log annuo USA in pp [IC95%] |\n|---|---:|---:|\n{chr(10).join(stat)}\n\nLa media 50/30/20 perde economicamente nel campione, ma i rispettivi intervalli per la differenza 50/50 includono un valore molto vicino allo zero (EU) e zero (USA): i risultati non possono essere interpretati come probabilità calibrata di fallimento futuro. Alcune varianti conservative o MINVAR mostrano intervalli con esclusione dello zero su uno dei mercati, ma si tratta di analisi post-ricerca.\n\n## 5. Stress costi\n\nStesso contratto, con coefficienti legacy `fee=0.003`, `stop_friction=0.005`; non sono spread broker osservati.\n\n| Architettura | CAGR EU | CAGR USA |\n|---|---:|---:|\n{chr(10).join(stress)}\n\nLe nuove medie non recuperano il divario nel test di costo più elevato. Il turnover, gli stop, il dettaglio annuale e tutti gli scenari sono nelle scorecard e nei log giornalieri.\n\n## 6. Validazione tecnica indipendente\n\n- 90 decisioni mensili per mercato. Alla chiusura originale, **125/125 feature Return e 42/42 Hybrid** coincidevano con il pannello congelato. L'appartenenza ai cluster resta quella mensile, non viene ricalcolata usando dati successivi.\n- USA: rank Return125 originale identico per 90/90 mesi e punteggi fino a precisione macchina. UE: per ottenere 90/90 classifiche identiche è necessario il checkpoint annuale **RSI_DOMAIN**; il raw percentile può differire fino a 0,0400 perché la popolazione di normalizzazione originale non coincide esattamente con il sottoinsieme eleggibile del test. Si utilizzano quindi soltanto **variazioni giornaliere** applicate agli score canonici originali.\n- ET e cinque teste OLC14 riaperte dal modello: predizioni grezze ET allineate a precisione macchina; XGBoost tolleranza massima osservata circa 7,15×10⁻⁸. Alcuni percentili presentano differenze su pareggi contigui dell'ordine di 0,00134. Non vengono dichiarati bitwise i rank dei giorni successivi.\n- Stadio contestuale OLC19: **90/90 Top2 storici esatti**, errore massimo negli score originali ~2,58×10⁻¹⁴ UE / 1,81×10⁻¹⁴ USA.\n- Motore OLC19: parità **bitwise 7/7 matrici** delle baseline in entrambi i mercati; corrispondenza di `alt` V6; tutti i 76 CAGR e MaxDD verificati indipendentemente con convenzione temporale originale.\n- L'ultima decisione del 30 giugno 2026 non dispone nel checkpoint delle due chiusure future: in quel caso resta il Top2 originale, senza inventare una previsione.\n\n## 7. Limiti e decisione\n\nLa strategia originale è **mensile**. Qui applichiamo gli stessi learner annuali alle due chiusure successive, tenendo fissi eleggibilità, cluster e modelli; è un'**estensione sperimentale giornaliera**, non una versione quotidiana già in uso e certificata del modello originale. L'aggancio agli score mensili serve a rispettare esattamente la baseline, ma non dimostra capacità fuori campione o esecuzione broker.\n\nRestano i limiti generali: universo point-in-time parziale, missing quote USA, adjusted versus total return, spread reali, slippage di stop/gap ed esecuzioni nello stesso giorno. Il FULL 2019–luglio 2026 non è un campione vergine. Le ottimizzazioni a posteriori dei pesi sarebbero ulteriore overfitting.\n\n**Decisione: non promuovere alcuna media dei veri ranking ML quotidiani.** Conservare OLC19 come baseline e OLC67 come candidato prospettico. La direzione più rigorosa non è esplorare altre percentuali sullo stesso storico, ma congelare eventualmente una regola di conferma con criteri economici verificabili e misurarla *prima* dei risultati futuri.\n\n## 8. Riproducibilità\n\nSorgenti di lavoro: `build_daily_features.py`, `score_daily_models.py`, `compose_daily_rank.py`, `sim_backend.py`, `run_native_daily_rank.py`, `analyze_olc102.py`, `make_report.py`; riferimento OLC19 originale e checkpoint annui OLC07/08/11/14 separati.\n\nOutput: `OLC102_SCORECARD.csv`, `OLC102_SELECTION_CHANGES.csv`, `OLC102_PAIRED_BLOCK6.csv`, `OLC102_ANNUAL_RETURNS.csv`, `OLC102_DAILY.csv.gz`, `OLC102_*_QA.json`, grafici NAV. Per riproduzione esatta servono i checkpoint originali identificati nel manifest; non vengono ridistribuiti nell'archivio sperimentale.\n'''
(R/'OLC102_REPORT_IT.md').write_text(report)
readme='''# OLC102: Real frozen ML daily-rank recomputation

Research-only: historical in-sample/retrospective replay. Original OLC19/OLC67 unchanged. Do not send trade orders.

Steps run: build_daily_features.py (EU/USA) -> score_daily_models.py (EU/USA) -> compose_daily_rank.py (EU/USA) -> run_native_daily_rank.py -> analyze_olc102.py -> make_report.py.

Original checkpoints (not included in compact ZIP): OLC19_Rischio_Rientro_Checkpoint_20261102.zip, OLC07_Calendario_Risultati_20261101.zip, OLC08_01_Pannelli_Verificati_20261101.zip, OLC08_02_Riferimenti_Riprodotti_20261101.zip, OLC08_03_RSI_Confronto_Verificato_20261101.zip, OLC11_02_Modelli_Verificati_20261101.zip, OLC14_Heads_Checkpoint_20261101.zip, EU_Original39_RH50_Checkpoint_20261031.zip. Source paths in scripts are session-specific and should be parameterized to run in a different workspace.

Output: 76 native replay rows, 90 monthly decisions per market, 125/125 and 42/42 baseline features, 90/90 original Top2. Uncorrected paired block6 confidence intervals; no prospective proof.

Use base scorer output anchored to original OLC19 monthly score and its as-of changes (EU raw percentiles are not precisely equal due eligible support). Monthly clusters are frozen for +1/+2 closes. Revaluation contextual is updated with same annual coefficient function at as-of time. These are explicit research conventions, not a proven live-production policy.
'''
(R/'README.md').write_text(readme)
print('REPORT',len(report),'README',len(readme))
