#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np,pandas as pd
R=Path(__file__).resolve().parent;O=R/'results';A=pd.read_csv(O/'OLC99_NATIVE_SCORECARD.csv');B=pd.read_csv(O/'OLC99B_NATIVE_SCORECARD.csv');C=pd.read_csv(O/'OLC99C_SCORECARD.csv');S=pd.concat([A,B,C],ignore_index=True)
SC=S[(S.fee==.001)&(S.timing=='DELAY3')&(S.period=='FULL')]
NAME={'E0_CONTEXT':'OLC19, Top2 50/50','E1_ANCHORED_20':'Economico Top10, 20%','E2_ANCHORED_35':'Economico Top10, 35%','E3_GLOBAL_ECONOMIC_20':'Economico universo, 20%','E4_NATIVE_ECONOMIC_20':'Economico nativo, 20%','E1_ALLOC_PRIOR':'Top10 20% + prior','E1_ALLOC_ML':'Top10 20% + ML'}
order=list(NAME)
fig,ax=plt.subplots(figsize=(12,5.5))
xx=np.arange(len(order));w=.36
for market,shift in [('EU',-w/2),('USA',w/2)]:
 vals=[float(SC[(SC.market==market)&(SC.arm==x)].cagr.iloc[0])*100 for x in order]
 b=ax.bar(xx+shift,vals,w,label=market)
 for p,v in zip(b,vals):ax.annotate(f'{v:.1f}',(p.get_x()+p.get_width()/2,p.get_height()),ha='center',va='bottom',fontsize=8)
ax.set_xticks(xx,[NAME[a] for a in order],rotation=23,ha='right');ax.set_ylabel('CAGR completo (%)');ax.legend();ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(O/'OLC99_CAGR_ARCHITECTURES.png',dpi=160);plt.close(fig)
fig,ax=plt.subplots(figsize=(8.5,5))
SK=pd.read_csv(O/'OLC99_ECONOMIC_SKILL_SUMMARY.csv')
vals=SK[['ctx_spearman','econ_spearman']].to_numpy();x=np.arange(len(SK))
ax.bar(x-.18,vals[:,0],width=.35,label='Contesto originale')
ax.bar(x+.18,vals[:,1],width=.35,label='Economico Top10 appreso')
ax.axhline(0,linewidth=1);ax.set_xticks(x,['Europa','USA']);ax.set_ylabel('Spearman mensile medio: punteggio / rendimento futuro');ax.legend();ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(O/'OLC99_RANKING_SKILL.png',dpi=160);plt.close(fig)
CI=pd.read_csv(O/'OLC99_DESCRIPTIVE_BLOCK6_CI.csv')
F=pd.read_csv(O/'OLC99_FORENSIC_SUMMARY.csv')
score=lambda m,arm:(SC[(SC.market==m)&(SC.arm==arm)].iloc[0])
rows=[]
for arm in order:
 for m in ('EU','USA'):
  s=score(m,arm)
  rows.append({'market':m,'strategy':NAME[arm],'arm':arm,'cagr_pct':round(100*s.cagr,3),'maxdd_pct':round(100*s.maxdd,3)})
T=pd.DataFrame(rows);T.to_csv(O/'OLC99_DECISION_TABLE.csv',index=False)
full=O/'OLC99_QA.json';qa=json.loads(full.read_text());qai=json.loads((O/'OLC99_INDEPENDENT_QA.json').read_text());qbi=json.loads((O/'OLC99B_INDEPENDENT_QA.json').read_text());qci=json.loads((O/'OLC99C_INDEPENDENT_QA.json').read_text())
monthly=pd.read_csv(O/'OLC99_FOR_FORENSIC_MONTHLY_SELECTION_DELTA.csv')
worst=monthly[monthly.pair_changed].sort_values('e1_minus_original_logpp').head(6)

body=f'''# OLC99 — Ranking economico Top10 e allocazione ML a stato contabile comune

**12 novembre 2026 — Ricerca retrospettiva, non promossa.** L'esperimento ricostruisce il ranker economico come *secondo stadio* dopo la FUSION originale e alloca solo fra gli ETF selezionati. Entrambi i moduli sono valutati e separati. Non ci sono trade live, futures acquistati o modifiche a OLC19/OLC67/`main`.

## Sintesi esecutiva

Il nuovo secondo stadio **non batte la selezione contestuale originale**. Sul periodo completo, con DELAY3, il controllo 50/50 ottiene **22,05% EU / 43,26% USA CAGR**. Un riordino economico conservativo Top10 (20% del punteggio) scende a **19,24% / 39,97%**; con un peso appreso per il Top1 passa a **18,28% / 40,57%**. Il learning dei pesi aiuta poco gli USA ma non recupera le scelte sbagliate a monte. Nel test più aggressivo (35%) il CAGR scende a **13,82% EU / 29,94% USA**, e il MaxDD europeo arriva a −43,01%.

Tre esperimenti con protocolli distinti sono stati eseguiti: (A) modello economico su soli Top10, (B) training esteso all'intero universo e applicazione invariata ai Top10, (C) target economico nativo da **1.780 controfattuali** su singoli ETF partendo dallo stesso stato pre-trade OLC19. **Tutti e tre non superano la baseline**. La verifica indipendente è PASS per calcoli e parità tecnica; non certifica capacità predittiva futura.

## 1. Architettura testata

`Return125 + ET/XGB → memoria originale → FUSION originale → Top10 → (nuovo ranking economico) → Top2 → (allocazione ML) → DELAY3 → V6/FAST_LOCK3 → conto`.

- Il Top10 è sempre composto dagli ETF con i dieci migliori punteggi FUSION **originali** fra quelli eleggibili. Il punteggio contestuale continua a essere calcolato dai layer nativi.
- **Stage A1 (principale):** Ridge α=100 con 12 indicatori anteriori al segnale (score dei diversi specialisti, differenza di score contestuale, momentum 5/10/21/63, volatilità 21/63 e drawdown 21). Target: rendimento log Open→Open del candidato meno mediana Top10, tagliato solo nel training a ±25%; pesi uguali per mese. Warmup almeno 24 mesi completamente maturi, training fino a t−2. Ranking combinato 80% contesto e 20% rank della previsione economica. La variante 65/35 è solo una sensibilità preregistrata.
- **Stage A2:** per il Top2 prodotto da A1, due allocatori con lo stesso intervallo teorico di pesi 0–100%: media storica dei vantaggi nativi da confronto 100/0 versus 0/100, e Ridge sulle differenze dei segnali ex-ante. Trasformazione dei valori previsti in pesi: `w_top1 = 0.5 + 0.5*tanh(mu/sigma)`, σ ottenuta dallo storico maturo con floor 100 logbp. Nessuna concentrazione forzata o ottimizzazione di soglie sul risultato corrente.
- I label economici dell'allocatore derivano da **cinque politiche di peso 0/25/50/75/100**, simulate dalla medesima fotografia del conto pre-trade, compresi blocchi di riacquisto, cash e esposizione V6. Il portafoglio conserva solo il ramo realmente selezionato, senza usare gli altri controfattuali per orientare la scelta corrente.

## 2. Risultati del portafoglio: stesso timing, stesso rischio, stessi costi

Costi `fee=0,001`, stop-friction `0,001`; FULL = febbraio 2019–prima apertura luglio 2026, con luglio 2026 non maturato per l'etichetta mensile. CAGR nativo a 252 sedute/anno. La tabella usa **sempre DELAY3**.

| Strategia | EU CAGR FULL | USA CAGR FULL | EU MaxDD FULL | USA MaxDD FULL |
|---|---:|---:|---:|---:|
'''
for arm in order:
 x=score('EU',arm);y=score('USA',arm)
 body+=f'| {NAME[arm]} | {100*x.cagr:.2f}% | {100*y.cagr:.2f}% | {100*x.maxdd:.2f}% | {100*y.maxdd:.2f}% |\n'
body+='''
![Confronto CAGR delle architetture](results/OLC99_CAGR_ARCHITECTURES.png)

Il controllo **OLC67 MinVar63+DELAY3+FAST_LOCK3**, proveniente da un altro esperimento già congelato, ha CAGR FULL **22,61% EU / 42,10% USA** e MaxDD **−26,59% / −27,60%**. Non è riadattato né incluso nel fitting OLC99. Le varianti OLC99 non lo dominano economicamente e in termini di rischio.

Con coefficienti costo aumentati a `0,003`, E1+ML scende a **14,72% EU / 32,09% USA**, contro **18,37% / 34,80%** del 50/50 con DELAY3. È un controllo di sensibilità del simulatore, non uno spread broker certificato.

## 3. I nuovi modelli migliorano davvero la classifica?

Sui mesi 2021–2026 con fit prequential disponibile e successivo risultato maturo (n=64 per mercato), le associazioni Spearman medie entro Top10 sono:

| Mercato | Score contestuale vs rendimento futuro | Previsione economica Top10 vs rendimento futuro | Gap oracle Top10 originale, log-pp/mese | Gap dopo E1, log-pp/mese |
|---|---:|---:|---:|---:|
'''
for x in SK.itertuples(index=False):body+=f'| {x.market} | {x.ctx_spearman:+.3f} | {x.econ_spearman:+.3f} | {x.ctx_oracle_gap_logpp:.2f} | {x.E1_oracle_gap_logpp:.2f} |\n'
body+='''
![Ranking dei singoli titoli del Top10: score originale e modello economico](results/OLC99_RANKING_SKILL.png)

La capacità del modello economico di ordinare i rendimenti successivi è debole: negli USA è addirittura negativa sul campione valutabile. Gli elevati *oracle gaps* indicano soltanto margini teorici che richiederebbero conoscere il futuro, non opportunità monetizzabili. Anche l'aumento occasionale dell'NDCG dell'intero Top10 non basta: il conto dipende dalle sole prime due posizioni.

## 4. Forensic delle sostituzioni costose

Il modello E1 cambia l'ordine e/o l'identità dei due ETF in **9/90** decisioni EU e **19/90** USA. Le sostituzioni economicamente più dannose a un mese, in log-punti percentuali relativi alla coppia originale, sono:

| Mercato | Segnale | Top2 originale | Top2 E1 | Differenza payoff statico E1−originale |
|---|---|---|---|---:|
'''
for x in worst.itertuples(index=False):
 body+=f'| {x.market} | {x.signal_date} | {x.ticker1_base}/{x.ticker2_base} | {x.ticker1_e1}/{x.ticker2_e1} | {x.e1_minus_original_logpp:+.2f} log-pp |\n'
body+='''
Il caso EU aprile 2023 (`EEPG.DE/VVSM.DE` → `EEPG.DE/EXX1.DE`) e il caso USA agosto 2025 (`ARGT/GDX` → `ARGT/EIDO`) sono esempi di errori selettivi ad alto costo. Sono diagnosticati **dopo** aver osservato il risultato e non possono diventare regole specifiche per ticker senza introdurre look-ahead o overfitting.

## 5. Il modello di allocazione sullo stesso stato

Sono state verificate **356 serie di controfattuali on-policy** (89 mesi × 2 mercati × 2 allocatori), ciascuna con cinque pesi e un esito della politica effettivamente scelta. Sono state riprodotte *bitwise* tutte le **sette matrici contabili native** per ciascuna delle quattro politiche on-policy: il risultato ricostruito mese per mese coincide esattamente con il replay integrale.

Con la stessa selezione E1 e DELAY3, in EU l'allocatore ML scende da **19,24%** a **18,28% CAGR**, mentre negli USA sale da **39,97%** a **40,57%**. Confrontato con la semplice media storica del premio Top1−Top2, l'allocatore ML perde in EU (**18,28% vs 18,86%**) e guadagna in USA (**40,57% vs 39,52%**), ma il bootstrap descrittivo non distingue stabilmente gli effetti dallo zero.

Le previsioni del differenziale operativo sono deboli e instabili; incrementare il peso su una previsione rumorosa amplifica errori già presenti nella scelta della coppia. Anche il rischio finale dipende dal percorso di stop e rientri, non solo dal rendimento medio statico.

## 6. Analisi aggiuntive B e C (successive al risultato A)

**OLC99B:** addestramento dello stesso Ridge sull'intero universo eleggibile (13.630 record di evento ETF EU, 13.410 USA), poi applicazione esclusiva al Top10 originale e identico mix 80/20. Risultato **20,49% CAGR EU / 36,50% USA**, sotto il riferimento. Questo riduce la plausibilità che la sola scarsità di esempi Top10 spieghi il fallimento.

**OLC99C:** 1.780 controfattuali nativi individuali, con la coppia/origine del mese mantenuta come stato iniziale comune. Stesso learner e mix, ma target relativo non sul prezzo Open→Open: sull'effettivo log-rendimento del ramo simulato dopo DELAY3/FAST_LOCK3. Risultato **20,44% EU / 34,52% USA**; il MaxDD europeo peggiora a **−35,55%**. In media sui 64 mesi maturi, la correlazione di rango delle previsioni di questa utilità nativa è circa **+0,029 EU / −0,114 USA**, contro il punteggio contestuale **+0,160 / +0,106**.

I due follow-up sono dichiarati come **ipotesi sviluppate dopo risultati negativi**, non come ulteriori validazioni indipendenti. Non giustificano una nuova griglia di hyperparameter tuning sul passato.

## 7. Intervalli, robustezza e decisione

Bootstrap descrittivo a blocchi di 6 mesi per differenza di **log-rendimento annualizzato**, non differenza di CAGR, fee `0,001`, DELAY3:

| Contrasto | Mercato | Δ annual log-pp | IC95% descrittivo |
|---|---|---:|---:|
'''
for x in CI.itertuples(index=False):
 arm=NAME.get(x.arm,x.arm);benchmark=NAME.get(x.benchmark,x.benchmark)
 body+=f'| {arm} − {benchmark} | {x.market} | {x.delta_annual_log_pp:+.2f} | [{x.lower95:+.2f}; {x.upper95:+.2f}] |\n'
body+='''
Gli intervalli non sono corretti per il numero elevato di esperimenti OLC01–98 e il periodo è già stato ripetutamente utilizzato. Non rivendichiamo alcuna nuova performance live, un premio di alpha provato o un miglioramento superiore al riferimento.

**Decisione: nessuna promozione di OLC99A/B/C.** Mantenere Return125, ET, XGB, memoria, FUSION, contesto e V6/FAST_LOCK3. La nuova pipeline è stata implementata e verificata come infrastruttura sperimentale ma non è un'alternativa preferibile ai modelli originali.

## 8. Prossima architettura con maggiore probabilità di valore

1. **Preservare la selezione FUSION→TOP2_CONTEXT_REVALUE.** La capacità previsiva dello score originale rimane superiore nei test disponibili. Non sostituire il ranking con una previsione di rendimento breve basata su poche decine di etichette mensili.
2. **Utilizzare il Top10 per un segnale complementare di rischio/opportunità, non per forzare un nuovo vincitore.** Analizzare a priori eventi in cui i candidati sono sostanzialmente equivalenti, differenziali di rischio e dati ortogonali con storico di pubblicazione verificato. OLC11/12 hanno già provato classificatori della coda alta senza trasferimento economico robusto; evitare di ripetere semplici blend degli score.
3. **Allocatore su coppia fissa e stesso stato.** L'infrastruttura OLC99 ora fornisce counterfactual 0/25/50/75/100 sullo stesso conto, ma con le feature attuali il learner non batte stabilmente il prior. La prossima validazione dovrebbe separare qualità della direzione dalla dimensione del rischio di errore grave, usando dati di mercato esterni effettivamente disponibili all'epoca.
4. **Valutazione temporalmente nuova** dopo 1 luglio 2026, con universo ETF e mask di quotazioni genuine, adjusted/total return coerenti, prezzi eseguibili, commissioni e stop realisticamente verificati. Un test nuovo va congelato prima dell'acquisizione degli outcome e confrontato con OLC19 e OLC67, senza scegliere parametri su 2024–2026 già visto.

## 9. Riproducibilità e conformità dell'audit

- Checkpoint originali OLC98, OLC19 e strumentazione OLC70 immutata (copie minime in `source/`), tutti gli input per questi replay e i codici sono nel pacchetto. Date, universi e 90 eventi per mercato congelati.
- **OLC99A:** 32 percorsi completi (inclusi due allocatori on-policy), 416 metriche native verificate indipendentemente; 356 intervalli mensili controfattuali a cinque pesi. Parità baseline OLC19 `7/7` EU e USA; stesse `7/7` matrici per quattro ricostruzioni on-policy.
- **OLC99B:** 8 percorsi nativi, 104 metriche indipendenti, 180 coppie verificate all'interno del Top10 originale.
- **OLC99C:** 4 percorsi nativi, 52 metriche indipendenti; 1.780 rami individuali da fotografie contabili comuni; parità originale con engine strumentato su `7/7` matrici.
- **Totale:** 44 percorsi nativi, **572 metriche di conto ricalcolate autonomamente**, 1.800 esempi candidato Top10 originali, 540 selezioni A, 180 B, 180 C. Le verifiche numeriche sono indipendenti dalle funzioni del simulatore, non una certificazione esterna della metodologia finanziaria.

Per riprodurre: `python run_olc99.py`, `python verify_olc99_independent.py`, `python run_olc99b.py`, `python verify_olc99b_independent.py`, `python run_olc99c.py`, `python verify_olc99c_independent.py`, `python evaluate_model_skill.py`, `python forensic_olc99.py`, `python make_report.py`. I dati giornalieri, le selezioni e i dettagli dei rami controfattuali sono disponibili in `results/`.
'''
(R/'REPORT_OLC99_IT.md').write_text(body,encoding='utf8')
print('Report generated',len(body),'chars, output',R/'REPORT_OLC99_IT.md')