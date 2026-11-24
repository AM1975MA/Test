from core24 import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64,shutil
import markdown
LABEL={'BASE':'U20','TRAIL_CASH':'Trailing U23','RAMP':'Rampa U23','TRAIL_CONFIRM':'Trailing confermato','TRAIL_HALF':'Trailing metà quota','TRAIL_FAST':'Rientro rapido','TRAIL_PROFIT':'Protezione dei guadagni','TRAIL_WIDE':'Banda più ampia','RAMP_GATED':'Rampa condizionata','CONFIRM_RAMP':'Conferma + rampa','HALF_RAMP':'Metà quota + rampa','PROFIT_RAMP':'Guadagni + rampa','WF_ECONOMIC':'WF economico','WF_PRUDENT':'WF prudente'}
def fmt(x):return f'{100*x:.2f}%'.replace('.',',')
def pp(x):return f'{100*x:+.2f}'.replace('.',',')
def main():
 s=pd.read_csv(OUT/'SUMMARY.csv');mo=pd.read_csv(OUT/'MONTHLY_DIAGNOSIS.csv');st=pd.read_csv(OUT/'STATISTICS.csv');cf=pd.read_csv(OUT/'CONFIDENCE_FAMILY.csv');reg=pd.read_csv(OUT/'REGIMES.csv');plans=pd.read_csv(OUT/'WF_PLAN.csv')
 def table(rules=RULES,bps=15,lag=0):
  out=['|Regola|EU CAGR / DD|USA CAGR / DD|TR CAGR / DD|','|---|---:|---:|---:|']
  for r in rules:
   cells=[]
   for m in MARKETS:
    z=s[(s.market==m)&(s.rule==r)&(s.bps==bps)&(s.lag==lag)].iloc[0];cells.append(fmt(z.cagr)+' / '+fmt(z.maxdd))
   out.append('|'+LABEL[r]+'|'+'|'.join(cells)+'|')
  return '\n'.join(out)
 a=s.query('bps==15 and lag==0');fig,axs=plt.subplots(1,2,figsize=(12,7.5),sharey=True)
 for ax,key,title,limit in zip(axs,['cagr','maxdd'],['Differenza CAGR (punti percentuali)','Riduzione drawdown (punti percentuali)'],[5,9]):
  z=np.array([[100*(a[(a.market==m)&(a.rule==r)].iloc[0][key]-a[(a.market==m)&(a.rule=='BASE')].iloc[0][key]) for m in MARKETS] for r in RULES[1:]])
  im=ax.imshow(z,cmap='RdYlGn',vmin=-limit,vmax=limit,aspect='auto');ax.set_xticks(range(3),MARKETS);ax.set_yticks(range(len(z)),[LABEL[r] for r in RULES[1:]],fontsize=9);ax.set_title(title,fontsize=11)
  for iy in range(len(z)):
   for ix in range(3):ax.text(ix,iy,f'{z[iy,ix]:+.2f}',ha='center',va='center',fontsize=10,color='white' if abs(z[iy,ix])>limit*.7 else '#172e3a')
  fig.colorbar(im,ax=ax,shrink=.7,pad=.03)
 fig.suptitle('Perseo U24 — stessa regola su tre panieri\nValori positivi favorevoli · 2 gennaio 2020 – 1 luglio 2026',fontsize=13);fig.tight_layout();fig.savefig(ROOT/'PERSEO_U24_CONFRONTO.png',dpi=150);plt.close(fig)
 fig,axs=plt.subplots(2,3,figsize=(13,6.5),sharex='col')
 colors={'BASE':'#626b77','PROFIT_RAMP':'#087f8c','CONFIRM_RAMP':'#c47619'}
 for j,m in enumerate(MARKETS):
  for r in colors:
   z=load(OUT/f'{tag(m,r,15)}.npz');ds=pd.DatetimeIndex(z['dates']);nav=z['nav'];axs[0,j].plot(ds,nav*10000,label=LABEL[r],c=colors[r],lw=1.3);axs[1,j].plot(ds,(nav/np.maximum.accumulate(nav)-1)*100,c=colors[r],lw=1.1)
  axs[0,j].set_title(m+(' · USD' if m=='USA' else ' · EUR'));axs[0,j].set_yscale('log');axs[1,j].set_ylabel('Drawdown %' if j==0 else '');axs[0,j].grid(alpha=.15);axs[1,j].grid(alpha=.15)
 axs[0,0].set_ylabel('Capitale, scala logaritmica');axs[0,0].legend(fontsize=8);fig.suptitle('Percorsi netti dei costi · scenari fissi, non selezione walk-forward');fig.tight_layout();fig.savefig(ROOT/'PERSEO_U24_PERCORSI.png',dpi=150);plt.close(fig)
 mt=['|Paniere|Mese|U20|Guadagni + rampa|Differenza pp|','|---|---|---:|---:|---:|']
 for m,month in [('EU','2020-03'),('EU','2025-03'),('EU','2020-04'),('USA','2024-12'),('USA','2022-01'),('USA','2020-04'),('TR','2020-08'),('TR','2021-03'),('TR','2026-04')]:
  z=mo[(mo.market==m)&(mo.rule=='PROFIT_RAMP')&(mo.bps==15)&(mo.lag==0)&(mo.month==month)].iloc[0];mt.append('|'+m+'|'+month+'|'+fmt(z.base_return)+'|'+fmt(z.new_return)+'|'+pp(z.delta)+'|')
 pt=['|Anno|WF economico 15bp|WF prudente 15bp|','|---|---|---|']
 for year in sorted(plans.year.unique()):pt.append('|'+str(year)+'|'+'|'.join(LABEL[plans[(plans.year==year)&(plans.bps==15)&(plans.procedure==r)].choice.iloc[0]] for r in ['WF_ECONOMIC','WF_PRUDENT'])+'|')
 ct=['|Paniere|Vantaggio log annuo pp|IC95% nominale pp|Intervallo simultaneo famiglia pp|','|---|---:|---:|---:|']
 for m in MARKETS:
  z=st[(st.market==m)&(st.rule=='PROFIT_RAMP')&(st.bps==15)&(st.lag==0)].iloc[0];f=cf[(cf.market==m)&(cf.rule=='PROFIT_RAMP')].iloc[0]
  ct.append('|'+m+'|'+pp(z.annual_log_delta)+'|'+pp(z.ci_low)+' / '+pp(z.ci_high)+'|'+pp(f.family95_low)+' / '+pp(f.family95_high)+'|')
 rt=['|Paniere|U20 2020–22|Nuova 2020–22|U20 2023–26|Nuova 2023–26|','|---|---:|---:|---:|---:|']
 for m in MARKETS:rt.append('|'+m+'|'+'|'.join(fmt(reg[(reg.market==m)&(reg.rule==r)&(reg.bps==15)&(reg.lag==0)&(reg.period==p)].iloc[0].cagr) for p in ['2020_2022','2023_2026'] for r in ['BASE','PROFIT_RAMP'])+'|')
 body=f'''# Perseo U24 — protezione condizionata e rientro

24 novembre 2026. **Migliorato il compromesso rendimento/drawdown, ma ancora nessun vantaggio comune dimostrato in walk-forward.** Il candidato più equilibrato è PROFIT_RAMP: 23,85% di CAGR EU, 39,99% USA, 25,36% TR. Riduce il drawdown rispetto a U20 su tutti e tre, a costo di 0,24 punti di CAGR USA. La variante migliore in Europa arriva al24,95% con drawdown−22,98%, ma danneggia gli altri panieri. Non viene adottata scegliendo retrospettivamente il mercato vincente.

Sono stati eseguiti120conti:108fissi/stress e12walk-forward. Sono simulazioni correlate. Nove regole nuove, tre controlli U23. Protocollo congelato nel commit locale c2f17b8 prima dei risultati; nessuna variante aggiunta dopo l'esito.

## Confronto completo

Apertura2gennaio2020–apertura1luglio2026. Capitale10.000; ticket1unità/ordine e15bp/lato, EUR EU/TR, USD USA. Quote frazionarie, cash senza interessi, niente leva sul conto o fiscalità. Drawdown marcato alle aperture. Il campione termina a luglio, non a novembre. Ranking e input125/42 congelati, senza riaddestramento del selettore.

{table()}

![Confronto](PERSEO_U24_CONFRONTO.png)

## Cosa è cambiato

La protezione originale usciva dopo una discesa dal massimo anche se la posizione era appena stata proposta. PROFIT_RAMP permette quella uscita solo dopo un guadagno dal prezzo iniziale della proposta almeno pari alla banda di volatilità. Rientra con il breakout originale; accelera il cooldown soltanto con S&P e proposta entrambi in recupero. La regola è identica nei tre panieri.

La banda è quella U23: clamp(2×sigma21×sqrt5,8%,18%). Il massimo riguarda il ciclo della proposta del selettore, non il costo medio effettivo di carico: non va interpretato come profitto contabile garantito. La rampa conserva stop individuali, allarmi sistemici e limite macro. Le condizioni usano esclusivamente chiusure precedenti; revisione ogni cinque sedute o al cambio della proposta.

Il trailing confermato richiede invece due chiusure deboli consecutive e rendimento21negativo. Migliora molto EU, ma non risolve la rotazione TR. Allargare soltanto la banda o rientrare più rapidamente non basta: TRAIL_FAST porta TR al21,85%, TRAIL_WIDE al23,46%. Ridurre a metà l'uscita attenua i danni senza creare un vantaggio comune.

![Percorsi](PERSEO_U24_PERCORSI.png)

## Diagnosi mese per mese

{chr(10).join(mt)}

La ricostruzione per ticker mostra che nel marzo2020 il vantaggio europeo deriva soprattutto dalla minore perdita su IS3N.DE (+5,72punti di contributo mensile) ed EXH1.DE (+1,93punti). Nel marzo2025 la riduzione di VVSM.DE vale+5,18punti, meno0,31di costi aggiuntivi. Nel dicembre2024 USA, invece, la gestione di SMH costa−1,72punti e i maggiori costi−0,15punti: l'uscita interrompe un percorso successivamente favorevole. Sono attribuzioni contabili, non una prova causale dell'efficacia futura dei segnali.

**Il92,62% del vantaggio logaritmico europeo di PROFIT_RAMP proviene da soli tre mesi: marzo2020, marzo2025, aprile2020.** Togliendoli in una verifica descrittiva, il differenziale log annualizzato scende da+2,51a+0,19punti. Su TR diventa negativo. Questa esclusione non è una strategia investibile né un test indipendente; misura la concentrazione del risultato.

Molti altri mesi hanno differenze positive minuscole perché il capitale più alto diluisce il ticket fisso. Non sono altrettante previsioni corrette. Con soglia di rilevanza5bp di rendimento mensile, PROFIT_RAMP migliora6mesi EU e ne peggiora0; USA8/5; TR3/3. I CSV contengono tutti i mesi, anche quelli sfavorevoli, e la decomposizione per ticker/costi dei casi principali.

CAGR per sottoperiodo; il confine comune è l'apertura3gennaio2023:

{chr(10).join(rt)}

La fragilità TR prima del2023 resta: −5,46%annuo contro−6,05% della base. Non è stata risolta dall'aggiunta di protezioni.

## Costi e ritardo

30bp per lato, ticket invariato:

{table(['BASE','PROFIT_RAMP','CONFIRM_RAMP','RAMP_GATED'],30,0)}

Una seduta di ritardo, confronto con BASE anch'essa ritardata:

{table(['BASE','PROFIT_RAMP','CONFIRM_RAMP','RAMP_GATED'],15,1)}

Il vantaggio EU di PROFIT_RAMP mantiene il segno; il piccolo vantaggio TR scompare con il ritardo. Gli stop originari restano tempestivi: lo stress differisce selezione, macro, difesa e nuovi segnali, non simula un'interruzione completa del broker.

## Walk-forward dell'intero processo di scelta

Ogni gennaio dal2022: scelta di una sola regola comune usando i24mesi precedenti; rendimento relativo minimo sui tre panieri e penalità drawdown. Versione prudente con limite bootstrap positivo. I dati di addestramento si fermano a chiusure anteriori al primo gennaio. Nessuna concatenazione di NAV, reset di capitale o cooldown. Prima del2022 si usaBASE. Gli scenari30bp selezionano sui propri costi.

{chr(10).join(pt)}

{table(['BASE','WF_ECONOMIC','WF_PRUDENT'])}

La scelta economica resta sotto U20 su TR (24,19%contro25,07%). La prudente replica EU/TR e cambia USA di appena+0,02punti: **non è un salto qualitativo**. Nei costi30bp la scelta economica aiuta EU/USA ma penalizza TR. I risultati fissi promettenti non equivalgono quindi a una procedura capace di sceglierli in anticipo.

## Confidenza statistica

Bootstrap appaiato a blocchi12mesi,3.000repliche, dipendenza fra panieri preservata. Intervalli sul vantaggio di log-rendimento annualizzato, non sul CAGR e non sulla probabilità che un ticker salga. La diagnostica simultanea, aggiunta dopo gli esiti senza nuove strategie, corregge approssimativamente i33confronti della famiglia U24 con max-|t| bootstrap:

{chr(10).join(ct)}

Gli intervalli simultanei includono zero. Anche l'evidenza europea nominalmente positiva si indebolisce correggendo i tentativi. La frequenza bootstrap del vantaggio minimo positivo è26,97% per PROFIT_RAMP: frequenza di ricampionamento, non probabilità futura. La correzione U24 non copre l'intero storico dei test Perseo;78mesi restano pochi per stimare eventi rari.

## Benchmark e interpretazione

Confronti U21 già ricalcolati sullo stesso periodo: S&P50014,78%EUR e15,31%USD; Nasdaq20,99%EUR e21,42%USD; tecnologia USA24,97%EUR con drawdown−33,57%; SMH40,60%USD con drawdown−46,91%. PROFIT_RAMP EU resta sotto la tecnologia in CAGR, con drawdown inferiore; USA resta vicino al CAGR SMH con drawdown inferiore. Sono confronti di strumenti diversi e rischio diverso, non stima di alpha. Le aperture mancanti EU/TR e le ipotesi di valorizzazione sono documentate inU21.

La letteratura di Levine/Pedersen, [Which Trend Is Your Friend?](https://www.aqr.com/insights/research/journal-article/which-trend-is-your-friend), invita a valutare implementazione, costi e costruzione del portafoglio oltre alla formula del filtro. È un riferimento metodologico, non una validazione di Perseo. Qui le prove mostrano che protezioni simili possono avere esiti diversi per via di stop, rientri e composizione.

## Verifiche e riproducibilità

- Tre BASE identiche aU20; nove controlli BASE/TRAIL/RAMP identici bit per bit aU23.
-120ricostruzioni indipendenti di quote e cash dagli ordini, riconciliazione P&L/commissioni.
- Nove perturbazioni future sui segnali di tutte le12regole, nove sui conti, tre sui dati di scelta annuale;30cutoff verificati e sei parità iniziali WF.
-15conti con attribuzione mensile per ticker;3.587righe, riconciliazione mensile con errore massimo1,45e−15.
-918file dei manifesti U20–U23 verificati: nessun file mancante o hash diverso.

QA.json e ATTRIBUTION_QA.json registrano i controlli. Il repository preparato include tutti gli stati necessari al replay dei107conti U20, input U22/U23, codice, protocolli, risultati e rapporti U20–U24. La ricostruzione dell'addestramento originale precedente richiede ancoraU19; non è stata eseguita qui.

Restano aperti: cataloghi non point-in-time completi, rettifiche non verificate con una seconda fonte, maschera osservazioni USA mancante, stop intraday sintetici e liquidità. Lo storico è già stato esplorato: il nuovo walk-forward non cancella il riuso dei dati.

## Decisione

U20 resta il riferimento. PROFIT_RAMP viene conservato come candidato di ricerca per un compromesso più favorevole, non promosso live. Il passo utile successivo riguarda soprattutto la selezione TR nei mesi2020–2022 e la previsione degli errori di rotazione; i soli filtri di protezione hanno mostrato rendimenti marginali e dipendenza da pochi episodi. Per dimostrarlo servono esiti maturati in avanti o storia non ancora usata, oltre a cataloghi e dati verificati.
'''
 for old,new in {'al24': 'al 24', 'drawdown−': 'drawdown −', 'eseguiti120conti': 'eseguiti 120 conti', '108fissi': '108 fissi', '12walk': '12 walk', 'Apertura2gennaio2020–apertura1luglio2026': 'Apertura 2 gennaio 2020–apertura 1 luglio 2026', 'Capitale10.000': 'Capitale 10.000', 'ticket1unità/ordine e15bp': 'ticket 1 unità/ordine e 15 bp', 'input125/42': 'input 125/42', 'rendimento21negativo': 'rendimento 21 negativo', 'al21,85%': 'al 21,85%', 'al23,46%': 'al 23,46%', 'marzo2020': 'marzo 2020', 'marzo2025': 'marzo 2025', 'dicembre2024': 'dicembre 2024', 'vale+5,18punti': 'vale +5,18 punti', 'meno0,31di': 'meno 0,31 di', 'costa−1,72punti': 'costa −1,72 punti', 'costi−0,15punti': 'costi −0,15 punti', '+5,72punti': ' +5,72 punti', '+1,93punti': '+1,93 punti', 'Il92,62%': 'Il 92,62%', 'aprile2020': 'aprile 2020', 'da+2,51a+0,19punti': 'da +2,51 a +0,19 punti', 'rilevanza5bp': 'rilevanza 5 bp', 'migliora6mesi': 'migliora 6 mesi', 'peggiora0': 'peggiora 0', 'USA8/5': 'USA 8/5', 'TR3/3': 'TR 3/3', 'apertura3gennaio2023': 'apertura 3 gennaio 2023', 'del2023': 'del 2023', '−5,46%annuo': '−5,46% annuo', 'dal2022': 'dal 2022', 'i24mesi': 'i 24 mesi', 'del2022': 'del 2022', 'usaBASE': 'usa BASE', 'scenari30bp': 'scenari 30 bp', '24,19%contro25,07%': '24,19% contro 25,07%', 'appena+0,02punti': 'appena +0,02 punti', 'costi30bp': 'costi 30 bp', 'blocchi12mesi,3.000repliche': 'blocchi 12 mesi, 3.000 repliche', 'i33confronti': 'i 33 confronti', 'positivo è26,97%': 'positivo è 26,97%', 'precedenti;78mesi': 'precedenti; 78 mesi', 'S&P50014,78%EUR e15,31%USD': 'S&P 500 14,78% EUR e 15,31% USD', 'Nasdaq20,99%EUR e21,42%USD': 'Nasdaq 20,99% EUR e 21,42% USD', 'USA24,97%EUR': 'USA 24,97% EUR', 'SMH40,60%USD': 'SMH 40,60% USD', 'inU21': 'in U21', 'aU20': 'a U20', 'aU23': 'a U23', '-120ricostruzioni': '- 120 ricostruzioni', 'le12regole': 'le 12 regole', ';30cutoff': '; 30 cutoff', '-15conti': '- 15 conti', ';3.587righe': '; 3.587 righe', 'massimo1,45e−15': 'massimo 1,45e−15', '-918file': '- 918 file', 'dei107conti': 'dei 107 conti', 'ancoraU19': 'ancora U19', 'mesi2020–2022': 'mesi 2020–2022'}.items():body=body.replace(old,new)
 (ROOT/'RAPPORTO_PERSEO_U24.md').write_text(body)
 html=markdown.markdown(body,extensions=['tables'])
 for name in ['PERSEO_U24_CONFRONTO.png','PERSEO_U24_PERCORSI.png']:
  html=html.replace('src="'+name+'"','src="data:image/png;base64,'+base64.b64encode((ROOT/name).read_bytes()).decode()+'"')
 (ROOT/'PERSEO_U24_ANALISI.html').write_text('<!doctype html><html lang="it"><meta charset="utf-8"><title>Perseo U24</title><style>body{font:16px/1.65 system-ui;color:#20303a;max-width:1160px;margin:40px auto;padding:0 22px}h1,h2{line-height:1.25;color:#124e60}h2{margin-top:40px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:9px;border-bottom:1px solid #d9e3e8;text-align:right}th:first-child,td:first-child{text-align:left}th{background:#edf3f5}img{width:100%;height:auto}a{color:#036978}</style>'+html+'</html>')
 shutil.copy2(OUT/'SUMMARY.csv',ROOT/'PERSEO_U24_SINTESI.csv');shutil.copy2(OUT/'MONTHLY_DIAGNOSIS.csv',ROOT/'PERSEO_U24_DIAGNOSI_MENSILE.csv')
 print('REPORT_COMPLETE',flush=True)
if __name__=='__main__':main()
