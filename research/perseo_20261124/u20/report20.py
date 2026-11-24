from analyze20 import *

def main():
 s=pd.read_csv(DEST/'SUMMARY_FINAL.csv');yr=pd.read_csv(DEST/'ANNUAL_FINAL.csv');stats=pd.read_csv(DEST/'CONFIDENCE_FINAL.csv');diag=pd.read_csv(DEST/'MONTHLY_DIAGNOSIS.csv');liq=pd.read_csv(DEST/'TR_UNIFIED_LIQUIDITY.csv');ctx=pd.read_csv(DEST/'CONTEXT_SUMMARY.csv');qa=json.loads((DEST/'QA_FINAL.json').read_text())
 def pct(x):return f'{100*x:.2f}%'.replace('.',',')
 def row(m,k):return s[(s.market==m)&(s.strategy==k)].iloc[0]
 table=['| Paniere | U19 comune: CAGR / DD | Nuova selezione: CAGR / DD | S&P500: CAGR / DD |','|---|---:|---:|---:|']
 for m in ['EU','USA','TR']:
  vals=[row(m,k) for k in ['LOCAL','UNIFIED','BENCHMARK']];table.append('|'+m+'|'+'|'.join(pct(x.cagr)+' / '+pct(x.maxdd) for x in vals)+'|')
 annual=['| Anno | EU U19 → nuovo | USA U19 → nativo conservato | TR U19 → nuovo |','|---|---:|---:|---:|']
 for y in range(2020,2027):
  cells=[]
  for m in ['EU','USA','TR']:
   a=yr[(yr.market==m)&(yr.year==y)];cells.append(' → '.join(pct(float(a[a.strategy==k].net_return.iloc[0])) for k in ['LOCAL','UNIFIED']))
  annual.append('|'+str(y)+('¹' if y==2026 else '')+'|'+'|'.join(cells)+'|')
 stress=['| Scenario | EU CAGR | USA CAGR | TR CAGR |','|---|---:|---:|---:|']
 stress.append('|15bp per lato|'+'|'.join(pct(row(m,'UNIFIED').cagr) for m in ['EU','USA','TR'])+'|')
 stress.append('|30bp per lato|'+'|'.join(pct(metrics(nav(m,'UNIFIED',30).index,nav(m,'UNIFIED',30).to_numpy())['cagr']) for m in ['EU','USA','TR'])+'|')
 c80=[]
 for m in ['EU','USA','TR']:
  a=ctx[(ctx.market==m)&(ctx.family==('NATIVE_REFERENCE' if m=='USA' else 'TRANSFER_LOCAL'))&(ctx.rule=='CORRELATION80')&(ctx.bps==15)].iloc[0];c80.append(pct(a.cagr)+' / '+pct(a.maxdd))
 body=f'''# Perseo U20 — un miglioramento strutturale, non ancora una strategia validata

23 novembre 2026. Ricerca retrospettiva; dati congelati dal2 gennaio2020 al1 luglio2026. Nessun ordine reale e nessuna modifica alle automazioni esistenti.

**Risultato:** trasferire le esposizioni del selettore USA in strumenti del paniere locale, usando il ranking locale quando manca una replica credibile, migliora il candidato su EU e Trade Republic. Il processo annuale che dovrebbe decidere quando adottarlo non conferma il risultato. Non dichiariamo risolto il problema della strategia unificata.

La novità è il trasferimento delle esposizioni. Sul paniere USA la trasformazione è l'identità: il40,23% annuo è il vecchio risultato preservato, non un nuovo guadagno attribuito a U20.

## Confronto omogeneo

{chr(10).join(table)}

CAGR netti dei costi simulati: capitale iniziale10.000, commissione1 unità monetaria+15bp per lato, quote frazionarie, nessuna leva sul conto, cash senza interesse, nessuna fiscalità. USA inUSD; EU eTR inEUR, ciascuno con benchmark nella propria valuta. Drawdown misurato alle aperture, non massimo intraday. Il benchmark paga il costo iniziale. I rendimenti non sono previsioni.

Il vecchio **USA nativo40,23% / DD−26,81%** rimane il riferimento forte. Il vecchio EU nativo è17,50% / DD−29,66%; U19LOCAL ha più CAGR ma anche più drawdown. Nessuno dei due viene nascosto. L'architettura di trasferimento porta EU da18,16% a20,78% eTR da17,96% a25,07%, cioè+2,62 e+7,11 punti annui. SuTR il DD passa da−35,66% a−29,53%.

![Capitale e drawdown](PERSEO_U20_CONFRONTO.png)

## Come funziona la stessa regola sui panieri

Il selettore canonico è quello USA originale, con i suoi segnali congelati e walk-forward ereditati. Per ogni ETF selezionato si cerca il proxy locale con il minor errore di tracking sui rendimenti a5sedute precedenti, fino a252date comuni; almeno26osservazioni. Si richiedono correlazione≥0,75 e tracking error normalizzato≤0,75. Si usa la differenza SXR8–SPY come proxy di conversione valuta e asincronia; non è una serie FX ufficiale.

La ricerca del proxy usa solo chiusure precedenti all'esecuzione. I proxy non sono scelti per il rendimento futuro o per il CAGR realizzato. Se non c'è un proxy qualificato, lo slot utilizza una delle due scelte LOCAL già disponibili. Pesi50/50; V6 originale come protezione. La regola è uguale per tutti, con il caso USA uguale all'identità. Il ranking LOCAL usato nel fallback conserva le feature e le previsioni della campagna U19; in U20 non abbiamo addestrato nuovi modelli.

Il test con cash al posto dei proxy mancanti rende14,04%EU e23,58%TR. Il completamento con LOCAL rende20,78%EU e25,07%TR. Il test senza filtro di qualità dei proxy rende14,86%EU e23,92%TR: cercare comunque una somiglianza non risolve l'assenza dell'esposizione.

**Confidenza di replica e confidenza di rendimento sono diverse.** Correlazione e tracking misurano se uno strumento rappresenta l'esposizione desiderata; non stimano la probabilità che quell'esposizione salga.

## Il problema economico emerso

Solo circa51%degli slot USA trova una replica qualificata nel vecchio EU e75%nelTR. Sono percentuali delle decisioni2020–2026, non pesi medi investiti. Semiconduttori comeSOXX/SMH trovano proxy in entrambi. UNG non passa mai; USL e numerose scelte di petrolio, palladio e altri metalli restano prive di una replica sufficientemente fedele. Queste assenze limitano il trasferimento del risultato USA. La semplice crescita dell'S&P500 dal2023 non implica che tutti i cataloghi offrano le esposizioni scelte dal motore.

Il risultatoTR migliora in44mesi su78, EU in39su78. SulTR marzo2020 passa da−21,55% a−10,17%; settembre2020 da−12,33% a−1,19%; settembre2024 da+0,54% a+15,70%. Esistono anche errori rilevanti: aprile2026 scende da+49,32% a+15,94% rispetto aLOCAL. Il nuovo candidato guadagna meno nel grande mese dell'idrogeno, pur avendo un CAGR complessivo migliore. Non dipende quindi soltanto dal conservare quel picco.

{chr(10).join(annual)}

¹2026è parziale, termina con la valorizzazione del1luglio. I rendimenti mensili/annuali attribuiscono ogni P&L apertura→apertura alla seduta iniziale. Questo criterio è coerente con il capitale finale ma può spostare un rendimento di confine rispetto alle vecchie tabelle U19. Nei selettori annuali si usano solo le valorizzazioni effettivamente disponibili prima del cutoff.

Il punto ancora debole è il2020–2022: il nuovoTR perde circa6,05%annuo, contro10,05%diLOCAL. Migliora ma resta negativo, mentre il benchmark guadagna. Il nuovoEU produce circa2,27%annuo nello stesso sottoperiodo. Dopo il2023 il nuovoTR arriva a circa59,98%CAGR: il miglioramento resta fortemente dipendente dal regime. Le finestre di regime usano aperture2020-01-02→2023-01-03 e2023-01-03→2026-07-01.

## Cosa ha detto il vero processo di adozione walk-forward

Abbiamo simulato anche la scelta dell'architettura, non soltanto l'esecuzione dei singoli modelli. Ogni gennaio dal2022 valuta i24mesi precedenti; la scelta è unica per i tre panieri. Richiede vantaggio positivo nel paniere peggiore, penalizza il deterioramento del drawdown e tiene un solo conto continuo, con costi alle transizioni.

La versione economica selezionaLOCAL nel2022, trasferimento con cash nel2023, trasferimento con fallbackLOCAL nel2024, poiLOCAL nel2025–2026. Ottiene **13,09%EU,36,76%USA,18,75%TR**. Peggiora nettamente EU e non raggiunge il vecchio USA nativo. Non viene promossa.

La versione con confidenza — limite inferiore unilaterale80% del minimo vantaggio, bootstrap appaiato a blocchi3mesi — non trova sufficiente evidenza e rimane sempreLOCAL. Anche il primo selettore annuale delle sei varianti di stop rimaneBASE. Questo fallimento viene conservato e ha precedenza sulle conclusioni ottimistiche ricavate dal miglior candidato fisso.

Questi sono processi causali sullo storico. La scelta di studiare queste architetture è avvenuta oggi, dopo molta ricerca precedente: **non esiste un holdout vergine né una verifica prospettica**. U20A, U20B, U20C eU20D hanno protocolli separati che mostrano l'ordine delle estensioni.

## Stop, contagio del rischio e rientro

Nel motore precedente uno stop individuale impone anche cooldown globale per3sedute. Separare lo stop locale dall'allarme sistemico porta il vecchioUSA da40,23% a44,31%CAGR e riduce il DD da−26,81% a−25,99%. SulTR LOCAL, invece, il CAGR scende17,96%→17,54%. Il beneficio USA non è stato presentato come beneficio comune.

Stop dimensionati sulla volatilità portanoUSA nativo46,60%, ma DD−32,18%; peggioranoTR. Il rientro dopo recupero della media5 non migliora la famiglia comune. Tutte le sette varianti, incluso il controllo senza protezione, sono registrate.

La variante contestuale isola lo stop solo con correlazione dei due ETF<0,80, stimata prima dell'apertura. Applicata al nuovo selettore produce:

| Variante comune di rischio | EU CAGR / DD | USA CAGR / DD | TR CAGR / DD |
|---|---:|---:|---:|
| Correlazione0,80 | {' | '.join(c80)} |

SuUSA aumenta il CAGR ma peggiora il DD rispetto al nativo. SuEU riduce leggermente il CAGR rispetto al trasferimento conV6BASE. Le soglie0,70 e0,90 sono conservate come sensibilità, senza promuovere il migliore numero. Il44,31%USA isolato e il25,43%TR contestuale appartengono a regole diverse: non vengono assemblati in una falsa strategia comune.

## Robustezza e confidenza

{chr(10).join(stress)}

Ritardare di una seduta le decisioni del nuovo selettore portaEU20,78%→17,59% eTR25,07%→28,71%. I risultati mostrano sensibilità all'attuazione, con effetti di segno opposto. Non è stata scelta la data più redditizia. Lo stress ritarda anche il segnale dell'alternativaV6; la protezione di mercato resta disponibile alla data corretta.

Bootstrap appaiato12mesi,3.000repliche sui78mesi, con gli stessi blocchi per tutti i mercati: il vantaggio logaritmico annualizzato del nuovo candidato rispetto aLOCAL ha intervallo95% **EU−6,89/+12,88 punti; TR−4,49/+16,75 punti**. Entrambi includono zero. Per il minimo fra tre panieri l'intervallo è−8,07/+6,69 punti. Le percentuali di repliche positive sono descrittive, non probabilità di successo futuro. Nessuna correzione integrale di tutti i tentativi storici.

La verifica di liquiditàTR trova{len(liq)}ordini, di cui{int((liq.participation>.05).sum())}oltre5%della media precedente del turnover e{int((liq.participation>.10).sum())}oltre10%; {int(liq.participation.isna().sum())}senza stima sufficiente. Massimo{liq.participation.max():.2f}volte la media. I15bp non sono una dimostrazione di eseguibilità su quei fondi. Il file dettaglia ogni ordine; non viene dichiarata capacità professionale del conto.

I cataloghi e le quotazioni rettificate non sono pienamente point-in-time. Le maschere di osservazione U19 includono controlli su barre complete e qualità retrospettiva; gli stop sono proxy su barre giornaliere. Questi limiti restano anche quando gli indicatori nuovi usano rigorosamente dati passati. Il DD intraday potrebbe essere peggiore.

## Verifiche e decisione

Parità bitwise dei5riferimenti con U19; verifica indipendente di quote, cash e ordini su{qa['accounts']}conti; riconciliazione P&L e commissioni; controlli di invarianza al taglio dello storico e alla modifica dei prezzi presenti/futuri sugli indicatori nuovi; date di replica strettamente precedenti all'esecuzione. I107conti comprendono controlli e stress correlati: non sono107prove statistiche indipendenti.

**Conserviamo il trasferimento delle esposizioni come candidato di ricerca. Non sostituiamo il vecchio USA conLOCAL e non promuoviamo il selettore annuale fallito.** Il prossimo problema concreto è separare il valore del trasferimento nei regimi negativi dalla disponibilità effettiva degli strumenti: prima di aggiungere nuove feature, occorre spiegare e ridurre le perdite2020–2022 e verificare l'esecuzione sui proxy selezionati. Questa campagna non dimostra ancora30%CAGR su tutti i panieri.

Fonti consultate: [Kaminski eLo, When do stop-loss rules stop losses?](https://dspace.mit.edu/entities/publication/bb69ca4b-0cdc-487f-831d-63b2e84fafee), per misurare il contributo incrementale della protezione; [Daniel eMoskowitz, Momentum Crashes](https://business.columbia.edu/faculty/research/momentum-crashes), per il rischio di rimbalzi dopo periodi di panico; [Moskowitz, Ooi ePedersen, Time Series Momentum](https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum), per distinguere segnali del singolo asset e ranghi di universo. Non sono prove della performance diPerseo e i loro portafogli non coincidono con i nostri ETF long-only. Il trasferimento per tracking è un'ipotesi operativa sviluppata qui.
'''
 # Normalize readability of numeric spacing in the written report without altering values.
 import re
 urls=[]
 def keep_url(match):
  urls.append(match.group(0));return 'URLTOKEN_'+('A'*len(urls))+'_'
 body=re.sub(r'https?://[^\s)]+',keep_url,body)
 body=re.sub(r'(?<=[a-zàèéìòù])(?=\d)', ' ', body)
 body=re.sub(r'(?<=\d)(?=[a-zàèéìòù]|[A-Z]{2})', ' ', body)
 body=re.sub(r'%(?=[A-Za-z])', '% ', body)
 for a,b in [('dal2','dal 2'),('dal2023','dal 2023'),('ETFselezionati','ETF selezionati'),('Kaminski eLo','Kaminski e Lo'),('Daniel eMoskowitz','Daniel e Moskowitz'),('Ooi ePedersen','Ooi e Pedersen'),('diPerseo','di Perseo')]:body=body.replace(a,b)
 body=re.sub(r'(?<=[a-zàèéìòù])(?=[A-Z]{2})', ' ', body)
 body=body.replace('conV6','con V6').replace('ilV6','il V6')
 for i,url in enumerate(urls,1):body=body.replace('URLTOKEN_'+('A'*i)+'_',url)
 (NEW/'RAPPORTO_PERSEO_U20.md').write_text(body)
 try:
  import markdown
  content=markdown.markdown(body,extensions=['tables'])
 except ImportError:
  import mistune
  content=mistune.create_markdown(plugins=['table'])(body)
 img=base64.b64encode((NEW/'PERSEO_U20_CONFRONTO.png').read_bytes()).decode();content=content.replace('src="PERSEO_U20_CONFRONTO.png"',f'src="data:image/png;base64,{img}"')
 (NEW/'PERSEO_U20_ANALISI.html').write_text('<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Perseo U20 — ricerca e verifiche</title><style>body{font:17px/1.6 system-ui,sans-serif;max-width:1120px;margin:40px auto;padding:0 24px;color:#203038;background:#f9faf8}h1,h2{line-height:1.2;color:#006b64}h2{margin-top:2em}table{border-collapse:collapse;width:100%;font-size:14px;background:white}th,td{padding:10px;border-bottom:1px solid #dce3df}th{background:#e2efea;text-align:left}img{width:100%;height:auto}a{color:#007f78}strong{color:#153f39}</style><body>'+content+'</body></html>')
 print('REPORT_WRITTEN',len(body))
if __name__=='__main__':main()
