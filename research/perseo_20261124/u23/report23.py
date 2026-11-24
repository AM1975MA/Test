from core23 import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64,shutil
sys.path.insert(0,str(ROOT.parent/'u23_deps'))
import markdown

LABEL={'BASE':'U20','CORE25':'25% nell’indice','CORE_WEAK':'25% condizionato','LEG_BENCH':'Metà dei titoli deboli → indice/cash','TREND_CASH':'Filtro di trend → cash','TRAIL_CASH':'Protezione dal massimo → cash','RECOVERY':'Rientro anticipato','RAMP':'Rientro graduale','TREND_RECOVERY':'Trend + rientro anticipato','LEG_RECOVERY':'Titoli deboli + rientro anticipato','WF_ECONOMIC':'Scelta annuale economica','WF_PRUDENT':'Scelta annuale prudente'}

def fmt(v):return f'{100*v:.2f}%'.replace('.',',')

def main():
    s=pd.read_csv(OUT/'SUMMARY.csv');a=s.query('bps==15 and lag==0');stats=pd.read_csv(OUT/'STATISTICS.csv')
    shutil.copy2(OUT/'SUMMARY.csv',ROOT/'PERSEO_U23_SINTESI.csv');shutil.copy2(OUT/'MONTHLY_DIAGNOSIS.csv',ROOT/'PERSEO_U23_DIAGNOSI_MENSILE.csv')
    fig,axs=plt.subplots(1,2,figsize=(12,6.8),sharey=True)
    for ax,metric,title,limit in zip(axs,['cagr','maxdd'],['Variazione CAGR (punti %)','Riduzione drawdown (punti %)'],[18,7]):
        matrix=np.array([[100*(a[(a.market==m)&(a.rule==r)].iloc[0][metric]-a[(a.market==m)&(a.rule=='BASE')].iloc[0][metric]) for m in MARKETS] for r in RULES[1:]])
        im=ax.imshow(matrix,cmap='RdYlGn',vmin=-limit,vmax=limit,aspect='auto');ax.set_xticks(range(3),MARKETS);ax.set_yticks(range(9),[LABEL[r] for r in RULES[1:]],fontsize=9);ax.set_title(title)
        for y in range(9):
            for x in range(3):ax.text(x,y,f'{matrix[y,x]:+.2f}',ha='center',va='center',fontsize=10,color='white' if abs(matrix[y,x])>limit*.65 else '#23343a')
        fig.colorbar(im,ax=ax,shrink=.7,pad=.03)
    fig.suptitle('Perseo U23 — differenze rispetto a U20, costi ordinari\nValori positivi favorevoli; nessuna variante migliora il CAGR su tutti i panieri',fontsize=13)
    fig.tight_layout();fig.savefig(ROOT/'PERSEO_U23_CONFRONTO.png',dpi=150);plt.close(fig)
    def table(bps=15,lag=0,rules=RULES):
        rows=['|Regola|Europa CAGR / DD|USA CAGR / DD|TR CAGR / DD|','|---|---:|---:|---:|']
        for r in rules:
            cells=[]
            for m in MARKETS:
                z=s[(s.market==m)&(s.rule==r)&(s.bps==bps)&(s.lag==lag)].iloc[0]
                cells.append(fmt(z.cagr)+' / '+fmt(z.maxdd))
            rows.append('|'+LABEL[r]+'|'+'|'.join(cells)+'|')
        return '\n'.join(rows)
    plan=pd.read_csv(OUT/'WF_PLAN.csv');pt=['|Anno|Costi 15 bp: economica|Costi 15 bp: prudente|Costi 30 bp: economica|Costi 30 bp: prudente|','|---|---|---|---|---|']
    for year in sorted(plan.year.unique()):pt.append('|'+str(year)+'|'+'|'.join(LABEL[plan[(plan.year==year)&(plan.bps==bps)&(plan.procedure==rule)].choice.iloc[0]] for bps in [15,30] for rule in ['WF_ECONOMIC','WF_PRUDENT'])+'|')
    body=f'''# Perseo U23 — nove altre strade e selezione walk-forward

24 novembre 2026. **Ho individuato due miglioramenti storici specifici di paniere e un compromesso comune fra rendimento e rischio. Nessuna delle nove regole migliora il CAGR su tutti i panieri; il processo walk-forward comune non supera U20.** Il riferimento rimane U20.

Sono stati eseguiti 102 conti: 60 confronti fissi ai due costi, 30 stress di ritardo e 12 conti walk-forward. Sono simulazioni correlate, non 102 esperimenti statisticamente indipendenti. La famiglia e le regole di scelta sono state scritte nel protocollo prima di produrre i risultati.

## Confronto completo

Periodo apertura 2 gennaio 2020–apertura 1 luglio 2026. Capitale iniziale 10.000; costi 1 unità per ordine e 15 bp per lato; EUR per EU/TR, USD per USA. Quote frazionarie, nessuna leva del conto, cash senza interesse, imposte escluse. Drawdown alle aperture. USA U20 è il nativo originale al 40,23%, non la variante separata al 44,31%.

{table()}

![Confronto completo](PERSEO_U23_CONFRONTO.png)

## I risultati utili

**Europa: protezione dal massimo della posizione.** Il CAGR passa da 20,78% a 22,68%, mentre il drawdown scende da −31,25% a −24,53%. La regola mette in cash la quota di un ETF quando perde una distanza dal massimo coerente con la volatilità, e rientra dopo una rottura delle dieci chiusure precedenti. Mantiene gli stop originali e rivaluta ogni cinque sedute o al cambio della proposta. La banda è fissata a clamp(2×sigma21×sqrt(5),8%,18%); non è stata scelta dopo il risultato.

Il beneficio europeo compare in entrambi i sottoperiodi: CAGR 2020–2022 da 2,27% a 3,16%, 2023–2026 da 39,36% a 42,40%. Ma la stessa regola porta USA al 36,06% e TR al 23,31%; su TR il drawdown peggiora a −33,48%. Non la promuoviamo selezionando il mercato vincente a posteriori.

**USA: rientro graduale dopo il cooldown.** Al posto di tre sedute tutte al 25%, la quota principale risale a 25%,50%,75%, con limite macro originale e blocchi individuali mantenuti. CAGR 40,23%→41,71%; drawdown −26,81%→−25,27%. Nel 2020–2022 il CAGR passa da 31,62% a 35,04%; nel 2023–2026 scende leggermente, da 48,10% a 47,72%. Europa resta al 20,66% e TR scende al 23,96%.

**Compromesso comune: 25% nell’S&P 500 del paniere.** Riduce la perdita massima su tutti i mercati, ma costa circa 1,21 punti di CAGR EU, 6,90 USA e 2,62 TR. Non è un aumento di rendimento. In TR attenua la debolezza 2020–2022, da −6,05% a −2,92% annuo, ma riduce il CAGR successivo da 59,98% a 49,54%. La quota è all’interno del portafoglio principale e resta sottoposta alle protezioni del motore; non è un investimento passivo esterno al conto.

Il rientro anticipato è la modifica meno invasiva: 21,05% EU, 40,71% USA, 24,62% TR. Sono variazioni contenute e senza evidenza di un vantaggio comune stabile.

## Le strade che hanno fallito

Il filtro di trend lento taglia anche i rimbalzi: su USA il CAGR scende al 23,99%, su TR al 20,08%. Aggiungere il rientro anticipato non recupera la perdita. Anche la riduzione dei titoli con rendimento negativo a 21 e 63 sedute sacrifica rendimento, specialmente negli USA. Il vincolo di una regola comune non è soddisfatto da un collage dei migliori risultati per mercato.

Il ranking e gli input 125/42 rimangono quelli congelati. Questo lavoro modifica allocazione e protezione; non riaddestra un selettore e non attribuisce alle regole di trend una probabilità calibrata di successo. Nessun filtro U22 è usato.

## Mesi che spiegano il risultato

|Caso|Mese|U20|Variante|Differenza|
|---|---|---:|---:|---:|
|Europa, protezione dal massimo|2020-03|−9,27%|−4,28%|+4,99 pp|
|Europa, protezione dal massimo|2025-03|−12,02%|−7,15%|+4,87 pp|
|Europa, protezione dal massimo|2025-04|−7,81%|−2,85%|+4,96 pp|
|Europa, protezione dal massimo|2024-12|+3,25%|−0,14%|−3,39 pp|
|USA, rientro graduale|2020-04|+1,51%|+6,26%|+4,75 pp|
|USA, rientro graduale|2026-02|+2,33%|−0,94%|−3,27 pp|
|TR, protezione dal massimo|2021-05|−8,31%|−12,89%|−4,58 pp|
|TR, filtro di trend|2024-09|+15,70%|+4,32%|−11,38 pp|

Sono esempi esplicativi, non la selezione usata per le metriche. Il CSV di diagnosi riporta tutti i mesi delle varianti e tutti gli scenari. Le differenze mensili sono punti percentuali di rendimento del mese; non si sommano per ottenere il CAGR. Il percorso dipende da posizioni, stop e capitale precedenti: una protezione aggiuntiva può anche peggiorare un mese o il drawdown, cambiando i successivi rientri.

## Robustezza a costi e ritardo

Costi raddoppiati a 30 bp per lato, ticket invariato:

{table(30,0,['BASE','CORE25','TRAIL_CASH','RAMP','RECOVERY'])}

Segnali differiti di una seduta, costi ordinari; il confronto corretto è con la BASE anch’essa differita:

{table(15,1,['BASE','CORE25','TRAIL_CASH','RAMP','RECOVERY'])}

I due miglioramenti locali conservano il segno in questi stress. Tuttavia, il ritardo cambia molto anche U20: TR passa da 25,07% a 28,62%, Europa da 20,78% a 17,89%. Non promuoviamo quindi il calendario ritardato dopo averne osservato il rendimento. Questo stress differisce ranking, macro g, alternativa difensiva e guardie nuove; gli stop originali rimangono tempestivi. Non simula un broker completamente indisponibile.

## Walk-forward dell’intero processo di scelta

Ogni gennaio dal 2022, una sola regola per i tre panieri viene scelta sui 24 mesi precedenti. La valutazione usa rendimenti relativi a U20 e una penalità per peggioramento del drawdown; la versione prudente richiede anche un limite bootstrap positivo. Il conto continua con le posizioni e il capitale già presenti. Non vengono concatenate curve di candidati.

La scelta usa esclusivamente patrimoni marcati a chiusure già concluse entro il 31 dicembre. Non entra il rendimento dell’ultima apertura di dicembre verso la prima apertura di gennaio. I cutoff sono salvati in WF_INPUT_CUTOFFS.csv. La valutazione finale resta apertura/apertura.

{chr(10).join(pt)}

Esito ai costi ordinari:

{table(15,0,['BASE','WF_ECONOMIC','WF_PRUDENT'])}

La procedura economica sceglie CORE25 nel 2022 e TRAIL_CASH nel 2026, tornando a BASE negli anni intermedi. Il risultato complessivo peggiora. La procedura prudente applica RECOVERY nel 2022 e poi BASE; resta vicina al riferimento ma leggermente sotto. Non c’è una selezione causale comune che realizzi i vantaggi dei migliori casi osservati ex post.

## Confidenza e controlli

Il bootstrap appaiato usa blocchi di 12 mesi e 3.000 repliche, con mesi condivisi fra panieri. Per Europa TRAIL_CASH il vantaggio log annualizzato stimato è +1,56 punti, con intervallo nominale 95% da −1,56 a +4,89. Per USA RAMP è +1,05 punti, intervallo da −0,38 a +2,36. Entrambi includono zero: **i miglioramenti storici locali non sono vantaggi statisticamente dimostrati**. Sono punti di log-rendimento, non intervalli sul CAGR. Non è stata calcolata una correzione integrale per tutti i tentativi storici del progetto.

Verifiche: BASE identica bit per bit a U20 sui tre panieri; 102 ricostruzioni indipendenti di quote e cash dagli ordini; riconciliazione commissioni/P&L; nove mutazioni future dei segnali su tutte le dieci regole; nove verifiche dei conti effettivi; tre mutazioni future delle curve usate per la scelta annuale; sei verifiche di parità del percorso iniziale WF e trenta cutoff annuali validi. Gli errori numerici sono in QA.json.

I dati ripristinati iniziano nel 2020: le nuove variabili usano un riscaldamento causale, senza inventare osservazioni precedenti. Il confronto termina a luglio 2026 e non è aggiornato ai prezzi di novembre. Restano i limiti originari di cataloghi non point-in-time, osservabilità USA incompleta, prezzi rettificati non verificati indipendentemente, esecuzioni degli stop a barra e liquidità. Lo storico era già stato esplorato: il walk-forward nuovo non lo rende indipendente dall’intera ricerca.

## Stato della ricerca

U20 rimane il riferimento. Le due linee locali vengono conservate per approfondimento, con esiti completi e senza adozione automatica. Il risultato utile è aver distinto protezione dalle perdite persistenti, utile in alcuni percorsi europei, e velocità del rientro, utile in alcuni percorsi USA. La difficoltà ancora irrisolta è riconoscere in anticipo quando applicarle con una regola comune, preservando il rendimento di TR. Nessuna modifica alle automazioni o a posizioni reali.
'''
    (ROOT/'RAPPORTO_PERSEO_U23.md').write_text(body)
    content=markdown.markdown(body,extensions=['tables'])
    im=base64.b64encode((ROOT/'PERSEO_U23_CONFRONTO.png').read_bytes()).decode();content=content.replace('src="PERSEO_U23_CONFRONTO.png"',f'src="data:image/png;base64,{im}"')
    (ROOT/'PERSEO_U23_ANALISI.html').write_text('<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Perseo U23 — altre linee</title><style>body{font:17px/1.55 system-ui,sans-serif;max-width:1240px;margin:40px auto;padding:0 24px;color:#26373c;background:#fafbf9}h1,h2{line-height:1.2;color:#106e65}h2{margin-top:2em}table{border-collapse:collapse;width:100%;font-size:14px;background:white}th,td{padding:9px;border-bottom:1px solid #dde5df}th{background:#e5efe9;text-align:left}img{width:100%}a{color:#007a74}</style><body>'+content+'</body></html>')
    print('REPORT_READY',len(body))

if __name__=='__main__':main()
