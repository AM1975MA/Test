from core22 import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64
sys.path.insert(0,str(ROOT.parent/'perseo_u19_deps'))
import markdown

LABEL={'BASE':'Perseo U20','NET21':'Vantaggio netto 21','LCB21':'Confidenza 21','LCB_MULTI':'Confidenza 5/21/63'}

def pct(x):return f'{x*100:.2f}%'.replace('.',',')

def main():
    s=pd.read_csv(OUT/'SUMMARY.csv');reg=pd.read_csv(OUT/'REGIMES.csv');diag=pd.read_csv(OUT/'MONTHLY_DIAGNOSIS.csv');stats=pd.read_csv(OUT/'STATISTICS.csv')
    s.to_csv(ROOT/'PERSEO_U22_SINTESI.csv',index=False)
    fig,axs=plt.subplots(1,2,figsize=(12,6),sharey=True)
    colors={'NET21':'#238c87','LCB21':'#d58a32','LCB_MULTI':'#7866a0'}
    for ax,bps in zip(axs,[15,30]):
        a=s[s.bps==bps]
        for j,rule in enumerate(RULES[1:]):
            dif=[]
            for m in MARKETS:
                v=a[a.market==m].set_index('rule').cagr
                dif.append(100*(v[rule]-v['BASE']))
            yy=np.arange(3)+(j-1)*.23
            ax.barh(yy,dif,height=.21,color=colors[rule],label=LABEL[rule])
            for y,v in zip(yy,dif):ax.text(v+(.08 if v>=0 else -.08),y,f'{v:+.2f}',ha='left' if v>=0 else 'right',va='center',fontsize=9)
        ax.axvline(0,c='#263b40',lw=1);ax.set_xlim(-7,3.3);ax.set_yticks(np.arange(3),MARKETS);ax.set_title(f'{bps} bp per lato + 1 per ordine');ax.set_xlabel('Variazione del CAGR rispetto a U20 (punti %)');ax.grid(axis='x',alpha=.15);ax.invert_yaxis()
    axs[0].legend(loc='lower left',fontsize=9);fig.suptitle('Perseo U22 — il filtro economico non migliora i tre panieri',fontsize=15);fig.tight_layout();fig.savefig(ROOT/'PERSEO_U22_CONFRONTO.png',dpi=160);plt.close(fig)
    def table(frame):
        lines=['|Paniere|Regola|CAGR|Max drawdown|Ordini|','|---|---|---:|---:|---:|']
        for m in MARKETS:
            for rule in RULES:
                r=frame[(frame.market==m)&(frame.rule==rule)].iloc[0]
                lines.append(f'|{m}|{LABEL[rule]}|{pct(r.cagr)}|{pct(r.maxdd)}|{int(r.orders)}|')
        return '\n'.join(lines)
    active=['|Paniere|U20|Netto 21|Confidenza 21|Confidenza 5/21/63|','|---|---:|---:|---:|---:|']
    for m in MARKETS:
        a=reg[(reg.market==m)&(reg.bps==15)&(reg.period=='2023_2026')].set_index('rule')
        active.append('|'+m+'|'+'|'.join(pct(a.loc[r,'cagr']) for r in RULES)+'|')
    bad=diag[(diag.rule=='NET21')&(diag.bps==15)].sort_values('delta').head(6)
    loss=['|Paniere|Mese|U20|Netto 21|Differenza|','|---|---|---:|---:|---:|']
    for r in bad.itertuples():loss.append(f'|{r.market}|{r.month}|{pct(r.base_return)}|{pct(r.new_return)}|{100*r.delta:+.2f} pp|')
    body=f'''# Perseo U22 — prova del filtro economico di cambio

23 novembre 2026. **Esito: proposta respinta nella forma provata.** Ho eseguito 24 conti continui: quattro regole, tre panieri, due livelli di costi. Ai costi ordinari tutte le varianti riducono il CAGR su tutti i panieri. Nessuna sostituisce U20.

## Risultati completi, costi ordinari

Periodo 2 gennaio 2020–1 luglio 2026. 10.000 unità iniziali, 1 unità per ordine + 15 bp per lato. EUR per EU/TR, USD per USA; quote frazionarie, cash senza interesse, fiscalità esclusa. Drawdown alle aperture. USA BASE è il nativo originale al 40,23%, non la variante separata di stop al 44,31%.

{table(s[s.bps==15])}

![Variazione del CAGR](PERSEO_U22_CONFRONTO.png)

NET21 perde circa 1,74 punti di CAGR in Europa, 5,44 negli USA e 1,32 su TR. Riduce appena gli ordini: 423→420, 645→637, 535→532. Il filtro prudente LCB21 riduce maggiormente le operazioni, ma perde circa 3,36, 2,87 e 5,31 punti di CAGR. Il drawdown dell’intero periodo non migliora in modo utile. La variante multi-orizzonte peggiora il drawdown europeo fino a −33,87%.

## Come è stato costruito il test

Il ranking e i suoi segnali derivati dai 125/42 input restano congelati. È stato aggiunto un modello di ammissione del cambio; non è un nuovo addestramento di tutte le feature. Il filtro usa una regressione ridge con sei variabili: differenze fra proposta e detenzione di rendimento log a 5/21/63 sedute, volatilità a 21 sedute, distanza dal massimo a 63 e quota di composizione da sostituire. Parametri comuni ai tre mercati, senza identificatori di ticker o mercato fra i predittori.

L’azione confrontata è comprare la proposta rispetto a mantenere le quote realmente presenti nel conto, valorizzate alla chiusura precedente. I costi stimati includono entrambi i lati necessari al cambio e i ticket. Il veto mantiene il precedente target; non provoca ribilanciamenti quotidiani artificiali. Stop, esclusioni, riduzioni di rischio e rientri da cash conservano la precedenza. Le alternative difensive sono quelle congelate U20.

- **NET21:** cambia se il vantaggio medio previsto a 21 sedute supera il costo.
- **LCB21:** richiede che superi il costo anche il limite prudente della stima della media, quantile bootstrap 20%.
- **LCB_MULTI:** confronto esplorativo a 5/21/63 sedute, vantaggio prudente per seduta e quantile 20%/3. L’orizzonte influenza la successiva rivalutazione; non impone una vendita alla scadenza.

Il bootstrap descrive incertezza della media stimata. **Non è una probabilità calibrata di guadagno del singolo trade.** Le etichette sono differenze di rendimento buy-and-hold apertura/apertura; non includono gli stop. Il conto finale include invece tutti gli stop e i costi: questo disallineamento fra previsione e decisione operativa è un limite della versione provata.

## Walk-forward effettivo e limiti temporali

Refit a gennaio con etichette completamente maturate prima dell’inizio dell’anno. Standardizzazione e coefficienti sono stimati soltanto sul passato. Il training pesa in modo uniforme mercato e mese; il bootstrap usa blocchi di tre mesi comuni ai mercati, senza trattare EU, USA e TR come indipendenti.

La soglia fissata nel protocollo richiede almeno 18 mesi distinti per ciascun mercato. Con i campioni validi disponibili **i primi modelli sono utilizzabili nel 2023**, non nel 2022: l’Europa non raggiunge prima il requisito. Le prime decisioni filtrate sono 3 gennaio 2023 per EU/USA e 1 marzo 2023 per TR. Il 2020–2022 resta identico a BASE; quindi questo esperimento non risolve il periodo debole antecedente al 2023 e non può presentare un miglioramento su quel tratto.

CAGR del solo periodo 3 gennaio 2023–1 luglio 2026:

{chr(10).join(active)}

Tutti questi anni sono già stati usati nella ricerca del progetto. La cronologia del nuovo filtro è verificata, ma ciò non trasforma lo storico in un holdout indipendente. Non abbiamo scelto dopo il test una regola diversa per ciascun paniere.

## Cosa ha fallito, mese per mese

Il filtro non distingue abbastanza bene i cambi utili da quelli evitabili. La riduzione delle operazioni elimina anche rotazioni vantaggiose. Questi sono i sei mesi con maggiore deterioramento del filtro NET21; il file MONTHLY_DIAGNOSIS.csv contiene tutti i mesi, inclusi i miglioramenti:

{chr(10).join(loss)}

Un caso concreto: il 2 maggio 2023 il portafoglio europeo propone di sostituire EL4C.DE con VVSM.DE, mantenendo EEPG.DE. NET21 stima un vantaggio di circa 0,028% contro un costo di 0,174% e blocca il cambio; lo blocca anche nelle rivalutazioni successive di maggio. Il conto del mese passa da +4,08% di U20 a −5,19%. È un errore economico molto più grande del costo che il filtro tentava di risparmiare.

Un secondo caso: a gennaio 2023 negli USA viene inizialmente respinta la rotazione da EPOL/PALL a EWN/EIRL. Il rendimento mensile scende da +11,30% a +3,65%. Il risultato dipende anche dai successivi stop e dalle rivalutazioni: non equivale a un semplice rendimento statico dei quattro titoli.

Come controllo descrittivo, fra le valutazioni NET21 respinte con esito osservabile, la proposta avrebbe superato la detenzione e il costo stimato nell’80% dei casi EU, 89,5% USA e 71,4% TR. I campioni sono appena 5, 19 e 14 e comprendono rivalutazioni sovrapposte: **non sono operazioni indipendenti né percentuali di successo affidabili**. Sono differenze buy-and-hold controfattuali, non P&L certificato con stop. Rafforzano la diagnosi di un filtro che scarta opportunità, senza dimostrare una regola alternativa vincente.

## Stress dei costi

Costi portati a 30 bp per lato, stesso ticket e stessa regola; il costo atteso entra coerentemente nelle decisioni:

{table(s[s.bps==30])}

L’unico caso favorevole è USA LCB_MULTI: CAGR 35,09% contro 32,96% della base, con drawdown −28,48% contro −28,11%. Europa e TR peggiorano. Non è un miglioramento unificato e non giustifica scegliere quella variante solo negli USA a posteriori.

## Statistica e verifiche

STATISTICS.csv riporta differenze annualizzate di log-rendimento dal 2023, con bootstrap appaiato a blocchi di 12 mesi e 3.000 repliche. Gli intervalli sono nominali e non correggono l’intera ricerca precedente. Per NET21 l’intervallo del peggior paniere è circa da −12,93 a −2,68 punti log annualizzati: il test non fornisce evidenza di miglioramento comune. Gli intervalli non sono intervalli sul CAGR e non vanno confusi con essi.

Verifiche completate: tre repliche BASE bit per bit uguali a U20; 24 ricostruzioni indipendenti di quote e cash dagli ordini; riconciliazione di commissioni e P&L; nove controlli delle variabili rispetto a mutazioni dei prezzi futuri; tre controlli del conto e delle decisioni dopo mutazioni future; tre verifiche che cambiare etichette non ancora mature non alteri i modelli già utilizzabili. QA.json contiene gli errori numerici e i cutoff.

Restano i limiti originari: panieri non completamente point-in-time, prezzi rettificati non verificati con un secondo fornitore, osservabilità USA incompleta, stop a barra e liquidità non garantita. Nessun dato successivo a luglio 2026 è incluso nelle performance.

## Decisione di ricerca

Conservare U20. Respingo queste tre formulazioni del filtro, senza concludere che ogni gestione economica del turnover sia inutile. Questa versione tenta di controllare un selettore ricco con un modello aggiuntivo molto più semplice: le sue previsioni non giustificano il potere di veto sulle rotazioni.

La revisione da considerare deve stimare il valore della decisione comprensivo di protezioni e collegarlo alle previsioni del selettore, verificandone la calibrazione prima di usarlo come veto. Per affrontare il 2020–2022 serve inoltre una base di calibrazione precedente e realmente disponibile a quelle date. Non introduco tali modifiche dopo aver visto questi risultati nello stesso esperimento.

Codice, dati congelati, modelli annuali, ordini, decisioni, risultati mensili e protocollo sono conservati nell’archivio U22. Nessuna modifica alla strategia di riferimento o alle automazioni.
'''
    (ROOT/'RAPPORTO_PERSEO_U22.md').write_text(body)
    html=markdown.markdown(body,extensions=['tables'])
    data=base64.b64encode((ROOT/'PERSEO_U22_CONFRONTO.png').read_bytes()).decode()
    html=html.replace('src="PERSEO_U22_CONFRONTO.png"',f'src="data:image/png;base64,{data}"')
    (ROOT/'PERSEO_U22_ANALISI.html').write_text('<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Perseo U22 — prova del filtro economico</title><style>body{font:17px/1.55 system-ui,sans-serif;max-width:1120px;margin:40px auto;padding:0 24px;color:#24353a;background:#fafbf9}h1,h2{line-height:1.2;color:#126d68}h2{margin-top:2em}table{border-collapse:collapse;width:100%;font-size:14px;background:white}th,td{padding:9px;border-bottom:1px solid #dce3df}th{background:#e6efea;text-align:left}img{width:100%}a{color:#007f78}</style><body>'+html+'</body></html>')
    print('REPORT_READY',len(body))

if __name__=='__main__':main()
