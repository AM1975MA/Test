"""Italian research report, rendered from immutable financial outputs."""
from pathlib import Path
import argparse,json,re
import pandas as pd

def pct(x,d=2):return f'{100*x:.{d}f}%'.replace('.',',')
def num(x,d=2):return f'{x:,.{d}f}'.replace(',','@').replace('.',',').replace('@','.')
def table(headers,rows):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in rows)

def editorial_spacing(text):
    # Preserve code identifiers, scientific notation, and link destinations.
    parts=re.split(r'(`[^`]*`|\]\([^)]*\)|\b[A-Z][A-Z0-9_]*\d[A-Z0-9_]*\b|\b\d\.\d+e-\d+\b)',text)
    for i in range(0,len(parts),2):
        p=parts[i]
        p=re.sub(r'(?<=[a-zàèéìòù])(?=\d)',' ',p)
        p=re.sub(r'(?<=[a-zàèéìòù])(?=[A-Z])',' ',p)
        p=re.sub(r'(?<=\d)(?=[A-Za-zàèéìòù])',' ',p)
        p=re.sub(r'%(?=[A-Za-zÀ-ÿ])','% ',p)
        p=re.sub(r'\bEUR(?=\d)','EUR ',p)
        p=re.sub(r',(?=[A-Za-zÀ-ÿ])',', ',p)
        p=p.replace('×',' × ').replace('comprendezero','comprende zero').replace('includonozero','includono zero')
        p=p.replace('èzero','è zero').replace('aggiustatiC','aggiustati C').replace('riga«','riga «').replace('causa«','causa «')
        p=p.replace('3 o6','3 o 6').replace('3o6','3 o 6')
        parts[i]=p
    joined=''.join(parts)
    joined=re.sub(r'\bEUR(?=\d)','EUR ',joined)
    joined=re.sub(r'\bI(?=\d)','I ',joined)
    joined=joined.replace('S&P500','S&P 500').replace('bpositivo','`b` positivo')
    joined=joined.replace('campionato-','campionato -').replace('extra,27','extra, 27')
    return joined

def build(root):
    root=Path(root).resolve();a=root/'analysis'
    s=pd.read_csv(a/'ALL_SCORECARD.csv',float_precision='round_trip');base=s[s.scenario=='BASE'].set_index('arm')
    years=pd.read_csv(a/'ALL_ANNUAL_RETURNS.csv',float_precision='round_trip')
    seg=pd.read_csv(a/'ALL_SEGMENTS.csv',float_precision='round_trip')
    pairs=pd.read_csv(a/'PAIRED_COMPARISONS.csv',float_precision='round_trip')
    ms=pd.read_csv(a/'MATCHED_STATE_SUMMARY.csv',float_precision='round_trip')
    qa=json.loads((root/'validation/COMBINED_QA.json').read_text())
    src=json.loads((root/'validation/source_execution/SOURCE_EXECUTION_AUDIT.json').read_text())
    new='DEDUP_DUAL_TREND_OPP';old='DUAL21';best=base.loc[new];prior=base.loc[old]
    names={'PASSIVE':'S&P500 EUR — SXR8','LEADERS':'Due leader annuali','DUAL21':'Doppio selettore precedente',
           'LIQ_DUAL21':'Doppio selettore + liquidità','DEDUP_DUAL21':'+ vincolo di correlazione',
           new:'+ trend positivo delle opportunità'}
    first=table(['Configurazione','CAGR','MaxDD campionato','€10.000 finali','Giorni operativi/anno'],
        [[names[x],pct(base.loc[x,'cagr']),pct(base.loc[x,'maxdd_sampled']),num(base.loc[x,'end_equity'],0),num(base.loc[x,'trading_days_per_year'])] for x in names])
    stress=table(['Scenario','Precedente: CAGR','Nuovo: CAGR','Differenza CAGR','Nuovo: MaxDD'],
        [[label,pct(s[(s.arm==old)&(s.scenario==scenario)].iloc[0].cagr),pct(s[(s.arm==new)&(s.scenario==scenario)].iloc[0].cagr),
          num(100*(s[(s.arm==new)&(s.scenario==scenario)].iloc[0].cagr-s[(s.arm==old)&(s.scenario==scenario)].iloc[0].cagr))+' pp',
          pct(s[(s.arm==new)&(s.scenario==scenario)].iloc[0].maxdd_sampled)] for scenario,label in [('BASE','Base'),('ZERO_COST','Senza costi'),('DOUBLE_COST','Costi raddoppiati'),('LAG1','Una seduta extra'),('LAG2','Due sedute extra')]])
    annual=table(['Anno','Precedente','Nuovo candidato','SXR8'],
        [[str(y)+(' (parziale)' if y in (2020,2026) else '')]+[pct(years[(years.arm==arm)&(years.scenario=='BASE')&(years.year==y)].iloc[0].annual_return) for arm in (old,new,'PASSIVE')] for y in range(2020,2027)])
    period=table(['Segmento descrittivo','Precedente: CAGR','Nuovo: CAGR'],
        [[label]+[pct(seg[(seg.arm==arm)&(seg.scenario=='BASE')&(seg.segment==code)].iloc[0].cagr) for arm in (old,new)] for code,label in [('2021_2024','2021–2024'),('2025_2026','2025–ottobre2026'),('2021_2026','2021–ottobre2026')]])
    matched=table(['Scenario / intervalli','N','Vittorie / sconfitte / parità','Media incremento','Mediana incremento'],
        [[f'{r.scenario} / {"tutti" if r.subset=="ALL" else "scelta modificata"}',int(r.n),f'{int(r.wins)} / {int(r.losses)} / {int(r.ties)}',num(r.mean_increment_bps)+' bp',num(r.median_increment_bps)+' bp'] for r in ms.itertuples()])
    families=[('CLUSTER_DUAL21','Punteggi mediani per gruppo'),('CLUSTER_DUAL_PEERS2','Gruppi confermati da almeno2ETF'),
        ('CLUSTER_DUAL_RESID','Pesi da volatilità residua'),('CLUSTER_DUAL_REVERT','Tilt35/65 da inversione a1mese'),
        ('CLUSTER_DUAL4','Quattro gruppi'),('CLUSTER_DUAL_EXIT63','Uscita settimanale sottoSMA63'),
        ('CLUSTER_DUAL_TRAIL15','Uscita dal massimo63 a−15%'),('CAPITAL_3H','Capitale fra3orizzonti'),('CAPITAL_3H_TILT','3orizzonti + tilt delle opportunità')]
    familytab=table(['Strada','CAGR base','MaxDD campionato'],[[label,pct(base.loc[arm,'cagr']),pct(base.loc[arm,'maxdd_sampled'])] for arm,label in families])
    concentrated=table(['Orizzonte','Top3: CAGR','Top1: CAGR','Top1: MaxDD'],[[f'{h}sessioni',pct(base.loc[f'HORIZON{h}','cagr']),pct(base.loc[f'HORIZON{h}_TOP1','cagr']),pct(base.loc[f'HORIZON{h}_TOP1','maxdd_sampled'])] for h in (63,126,252)])
    full=[]
    for row in s[s.scenario=='BASE'].itertuples():
        q=s[s.arm==row.arm].set_index('scenario')
        full.append([row.stage,row.arm,pct(row.cagr),pct(row.maxdd_sampled),pct(q.loc['DOUBLE_COST','cagr']),pct(q.loc['LAG1','cagr']),pct(q.loc['LAG2','cagr']),num(row.trading_days_per_year)])
    fulltab=table(['Blocco','Configurazione','CAGR base','MaxDD base','CAGR costi2×','CAGR lag1','CAGR lag2','Giorni/anno'],full)
    report=f'''# OLC109 — Ricerca su selezione, opportunità e concentrazione degli ETF

**15 novembre 2026 · 40 configurazioni, 200 percorsi finanziari · universo2.096ETF EUR**

## 1. Esito e priorità aggiornata

Il risultato migliore di questa iterazione, nello scenario con costi, è **{pct(best.cagr)} di CAGR annuo**, contro **{pct(prior.cagr)}** del precedente doppio selettore. Il capitale simulato passa da EUR10.000 a **EUR{num(best.end_equity,0)}**, contro EUR{num(prior.end_equity,0)}. La differenza di CAGR è **{num(100*(best.cagr-prior.cagr))} punti percentuali**, con un patrimonio finale superiore del{pct(best.end_equity/prior.end_equity-1)}.

Il30% annuo richiesto **non è ancora raggiunto**: nessuno dei200percorsi lo supera, neppure eliminando i costi. Il migliore senza costi arriva al28,82%; lo scenario BASE con costi resta il confronto principale per l'obiettivo.

L'utente ha esplicitamente accettato drawdown maggiori e rinviato la scelta della protezione. **Il limite25% e il Calmar1 non vengono più usati per scartare i selettori.** Il nuovo candidato, con MaxDD campionato{pct(best.maxdd_sampled)}, rimane quindi una base di ricerca ammissibile. Il rischio viene misurato per la fase successiva. I campi tecnici `numeric_target_pass` dei risultati congelati conservano la definizione originaria; il criterio corrente è distinto in `current_cagr_target_pass` / `research_return_target_pass` e nel riepilogo analitico.

Il candidato è denominato `DEDUP_DUAL_TREND_OPP`: ranking individuale, vincolo sulle coppie troppo correlate e opportunità ammesse soltanto dentro un trend positivo. È il migliore **osservato dopo i test**, non un modello già validato per il futuro. Il campione è già stato esaminato più volte e i blocchi2/3 sono esplicitamente adattivi.

## 2. Confronto sullo stesso conto e sugli stessi dati

Periodo2marzo2020–30ottobre2026; EUR10.000 iniziali; EUR1 per ordine più0,15% del controvalore per ciascun lato; prezzi EUR aggiustati; unità economiche frazionarie; cassa con rendimento0; imposte escluse. Decisioni dopo il Close, esecuzione all'Open successivo disponibile secondo le regole congelate; nessuna leva di conto o posizione corta. Il DD è campionato a Open/Close, non sull'intera traiettoria intraday.

{first}

Le prime due righe attive di controllo mantengono le regole precedenti. Il solo filtro di liquidità riduce il rendimento del doppio selettore a16,82%: parte del risultato precedente proveniva da ETF con scambi contenuti sulla sede osservata. Mantenendo tale filtro, evitare coppie troppo correlate porta17,84%. Aggiungere il requisito di trend positivo **soltanto agli sfidanti recenti** porta25,75%: il miglioramento controllato su quella base è7,91punti di CAGR.

Questo non significa che ogni filtro migliori il modello. Il primo tentativo basato su mediane di gruppo peggiora il rendimento; i risultati negativi rimangono nell'archivio e nella tabella completa. Il passaggio ai gruppi cambiava sia l'ordinamento sia l'ETF rappresentante: il secondo blocco serve precisamente a distinguere tale effetto dal semplice vincolo di correlazione.

## 3. Regole del candidato al25,75%

### Universo e idoneità

L'universo contiene2.096ISIN di ETF quotati su Xetra in EUR, dopo le verifiche V3 già svolte. Non coincide con tutti gli ETF mondiali e non tutti sono selezionabili in ogni data. Ogni ETF deve avere almeno253 osservazioni effettive complessive, almeno241nelle253sessioni recenti, prezzo osservato nella data di segnale e mediana del controvalore scambiato nelle ultime63sessioni di almenoEUR100.000. Gli zeri e le osservazioni non accettate contano come zero nella mediana. È un filtro sui dati della sede, non una stima completa della liquidità dell'ETF.

### Selettore dei leader

Si ordinano i singoli ETF per log-rendimento nelle ultime252sessioni. Il primo diventa il leader principale; il secondo è il successivo della graduatoria con correlazione126non superiore a0,85 rispetto al primo. La parità viene risolta per ISIN. Se il secondo posto non si riempie, la sua metà resta cash.

### Selettore delle opportunità

Si misura il rendimento recente21sessioni e lo si confronta con il precedente tratto105sessioni, diviso per5. In simboli, con prezzi aggiustatiC:

`b = log(C[t]/C[t−21]); a = log(C[t−21]/C[t−126])/5; accelerazione = b−a`.

Lo sfidante deve avere bpositivo, appartenere al terzo superiore della graduatoria recente, provenire da una graduatoria del tratto precedente inferiore al terzo superiore e avere accelerazione positiva. Deve stare sopraSMA63, avere correlazione126<=0,85 con il primo leader ed essere distinto dai due leader iniziali.

La nuova condizione richiede inoltre **rendimento252positivo, rendimento63positivo e prezzo sopraSMA200**. Il filtro riguarda gli sfidanti; non riscrive la graduatoria dei leader. Tra gli emergenti compatibili si prende il primo per accelerazione. Sostituisce il secondo leader solo se il suo rendimento21è maggiore; altrimenti resta il leader, senza cercare un altro sfidante retrospettivamente favorevole.

### Capitale e tempi

Due posti50/50, revisione mensile, esecuzione Open successivo, banda3% per limitare piccoli ribilanciamenti. Nessun controllo aggiuntivo di volatilità o stop nella variante candidata. Il conto BASE genera226ordini in circa80giorni di negoziazione, **12,00giorni operativi annui**: sono giornate con ordini, non226decisioni indipendenti. I pesi effettivi possono deviare dal50/50 per movimento dei prezzi, banda o esecuzioni parziali.

La logica economica è circoscritta: una ripresa recente non basta da sola a giustificare l'abbandono del leader. Si richiede che il recupero sia coerente con un trend già positivo. Questa interpretazione è un'ipotesi sostenuta dal confronto storico, non una legge di mercato.

## 4. Controfattuali a parità di capitale e posizioni

Per isolare il filtro del trend sono stati ricostruiti80intervalli BASE e80LAG2. Ogni volta i due rami partono dalle stesse unità, dalla stessa cassa e dal medesimo stato effettivo del candidato. Uno mantiene il filtro, l'altro usa `DEDUP_DUAL21`. Il target diventa eseguibile soltanto alla sua data dovuta; eventuali ordini precedenti sarebbero comuni ai due rami. La chiusura è quella della decisione successiva, prima della nuova esecuzione. I160replay del ramo effettivo coincidono esattamente con i NAV registrati.

{matched}

Il filtro cambia40decisioni su80. Nei40intervalli modificati, BASE registra24vantaggi e16svantaggi; l'incremento medio è87,26bp del capitale iniziale dell'intervallo, la mediana176,08bp. Con due sedute extra,27vantaggi e13svantaggi; media90,19bp. I40intervalli non modificati restano esplicitamente nella riga«tutti», dove la mediana èzero.

Queste medie **non sono un CAGR, non vanno moltiplicate per12 e non formano una strategia composta**. Sono interventi descrittivi che ripartono ogni mese dallo stato effettivo del candidato. La scelta del candidato dopo i risultati resta un limite anche per questa diagnosi.

## 5. Tutti gli anni, compreso il2024

{annual}

Il candidato migliora il confronto con il precedente in cinque dei sette anni riportati, ma rinuncia a una parte importante del guadagno2023. Il2024 passa da−4,89% a+33,95%; il2025 da+46,27% a+57,17%. Nel2026 parziale rimane una perdita,−15,30%, contro−17,70% del precedente. Il2021 resta negativo. Non si nascondono questi anni e non si presenta una distribuzione regolare dei rendimenti.

Il miglioramento complessivo **non dipende da un2020 ancora più favorevole**: il candidato rende meno in quel tratto iniziale. Escludendo2020 per una lettura descrittiva, senza chiamarla holdout, il confronto è:

{period}

I rendimenti annuali2020e2026sono parziali. I CAGR dei segmenti sono annualizzati sui giorni effettivi; il dato annuo2020in tabella è invece il rendimento cumulato del tratto marzo–dicembre. Non vanno confusi.

## 6. Costi e ritardi di esecuzione

{stress}

La versione nuova supera la precedente in tutti i cinque scenari comparabili. Rimane però sensibile all'esecuzione: il CAGR scende da25,75% a18,65% con una seduta extra e13,19% con due. La robustezza relativa è migliore; il livello assoluto richiesto non è raggiunto. Senza costi si arriva28,82%, dunque la distanza dal30% non viene spiegata interamente dalle commissioni.

Nel BASE del nuovo candidato13ordini su226 raggiungono almeno il10% del controvalore giornaliero della sede; nessuno raggiunge il100%, ma il massimo è48,64%. Il precedente ne aveva61su230 oltre il10% e6oltre il100%. Il filtro migliora questo indicatore, ma non dimostra che ogni ordine fosse eseguibile all'Open con15bp d'impatto. Nel LAG2 del candidato la quota massima arriva70,24%.

Per l'intero studio, gli scenari producono49.055ordini, di cui1.316almeno al10% e107almeno al100% del controvalore giornaliero riportato; il massimo è27,01volte. Questi conteggi aggregano percorsi correlati e non sono osservazioni di mercato indipendenti. Il volume della singola sede non include tutte le fonti di liquidità dell'ETF, ma i casi segnalati impediscono di certificare il modello di esecuzione.

## 7. Strade scartate o tenute separate

Sono stati conclusi tre blocchi:110percorsi per gruppi, pesi e protezioni;50per ranking individuale con vincoli mirati;40per orizzonti e concentrazione. I protocolli dei blocchi2/3 sono stati congelati prima dei rispettivi rendimenti, **dopo** aver osservato i blocchi precedenti. Si tratta di40configurazioni×5scenari, non di200ipotesi statisticamente indipendenti.

{familytab}

Il clustering completo non migliora automaticamente la selezione: mediane e sostituzione con il componente più scambiato possono diluire proprio il segnale ricercato. La conferma di almeno due ETF in un gruppo ha risultati più interessanti in alcuni anni, ma17,61% di CAGR complessivo non supera il candidato. Le allocazioni da volatilità residua e dalla semplice inversione a1mese non producono il salto richiesto.

Le uscite settimanali sottoSMA63 e dal massimo63sono state testate prima della richiesta di rinviare la protezione. Non vengono promosse: nei casi osservati possono vendere durante una flessione e mancare la ripresa. RISK15/20sui gruppi confermati hanno ridotto il rischio, per esempio13,19%CAGR e−19,44%DD perRISK20; sono una misura del costo storico della riduzione del rischio, non il filtro con cui scartare ora i selettori.

### La concentrazione è stata provata esplicitamente

{concentrated}

Per questi controlli, orizzonte e filtro di idoneità sono identici all'interno di ogni riga; cambia il numero di posizioni. Le versioni Top1possono investire100% in un ETF. Il vincitore a3o6mesi produce perdite elevate e CAGR negativo: accettare un drawdown maggiore non rende automaticamente più redditizio il selettore. Il leader annuale Top1rende12,79%, ancora sotto il candidato.

La combinazione di tre portafogli a63/126/252sessioni è una nuova architettura di capitale. Ogni portafoglio sceglie tre individui, con un solo componente per gruppo e corr<=0,85all'interno del portafoglio. La miscela può contenere più ETF dello stesso gruppo, ma il peso target aggregato del gruppo rimane al massimo1/3. Il tilt50/25/25sceglie il portafoglio con maggiore accelerazione recente positiva, soltanto quando tutti sono pienamente investiti; conserva titoli e gross rispetto alla miscela uniforme. Il guadagno del tilt è appena0,69punti di CAGR, senza evidenza di stabilità statistica. La miscela cambia anche numero e composizione dei titoli: non isola da sola una pura causa«diversificazione».

## 8. Quanto è solida l'evidenza

Il nuovo candidato ha un vantaggio storico concreto, ma non è dimostrata una superiorità persistente. Il confronto accoppiato su80rendimenti mensili usa bootstrap circolare a blocchi di6mesi,10.000repliche,seed109. Per il candidato rispetto al precedente, l'intervallo95% della **differenza annualizzata dei log-rendimenti relativi** va da−10,58% a+15,41% e comprendezero. Non è un intervallo per i3,38punti di differenza dei CAGR. Tutti i16contrasti descrittivi calcolati hanno intervalli che includonozero.

Il bootstrap conserva l'accoppiamento temporale, ma non corregge la scelta del modello dopo numerose prove, il survivorship o i limiti dei prezzi. Non è un test definitivo dell'assenza di segnale e non convalida il candidato. Il dato che guida il seguito è più limitato: il filtro delle opportunità ha migliorato i conti e il confronto sullo stesso stato; ora merita una verifica su informazione nuova e su esecuzioni più credibili.

La ricerca precedente del repository è stata utilizzata prima di scegliere i test. OLC74/99 avevano già provato apprendimento dei pesi e ranking economico Ridge con etichette mature e controfattuali, senza un vantaggio affidabile; OLC102/103 avevano trovato problemi nello smoothing e nella stabilizzazione; OLC105 aveva già provato il trasferimento congelato del veroFUSION. Per questo non si presenta una regressione simile come innovazione. Il modelloFUSION originale non è stato ricreato approssimativamente né rinominato: questa ricerca usa regole trasparenti distinte, con copie e URL immutabili delle evidenze precedenti.

## 9. Verifiche eseguite e limiti dei dati

**Audit indipendente PASS su200conti e49.055quantità/tempi di ordine**, con revisori di conto e di segnale che non importano il motore o i selettori di produzione. Sono stati ricostruiti16.925istruzioni,3.121target,80partizioni mensili e13.528gruppi;300ISIN e591.000righe uniche di controvalore sono confrontati con i CSV sorgente. La maggiore differenza NAV/cassa èEUR{qa['max_nav_cash_error']:.2e}. Le11baseline precedenti disponibili coincidono; i4stress passivi assenti nel vecchio archivio sono dichiarati non disponibili.

La suite locale ha51test superati. I120vettori di scelta delle40configurazioni su tre date reali restano identici quando si modifica il futuro. Sei alterazioni intenzionali di target, quantità, costo o tempi vengono respinte. Un residuo numerico di unità richiede parsingCSV `round_trip` nell'auditor: il contatore viene riconciliato senza cambiare risultati finanziari.

Il controllo separato delle storie effettivamente negoziate copre257ISIN: nessun riempimento suOpen non accettato, nessuna discrepanza tra prezzi accettati e copie sorgente, nessun nuovo evento materiale di fonte utilizzato rispetto all'audit V3. Sette eventi aggiuntivi sono contesto di aggiustamento per dividendi, non errori dimostrati; gli eventi già noti sono conservati. Nessuna osservazione viene cancellata perché produce una perdita. L'età massima deiClose detenuti e deiClose usati al posto di unOpen mancante è5giorni di calendario, senza casi superiori.

Restano limiti precisi:

- **Catalogo attuale:** non sono ricostruiti tutti i fondi chiusi o usciti dall'universo. La selezione storica priva di survivorship bias non è certificata.
- **Prezzi aggiustati e disponibilità:** il volume positivo del giorno completato filtra retrospettivamente gliOpen; tale volume non è noto all'apertura. Non è certificato il vintage storico dei fattori di aggiustamento.
- **Investibilità:** volume e prezzi della sede non descrivono spread, profondità o capacità dell'asta di apertura. Gli stress di ritardo e costo sono parziali.
- **Contabilità economica:** unità frazionarie, imposte escluse e cassa senza interessi. Il drawdownOpen/Close può sottostimare il minimo intraday.
- **Ricerca adattiva:** tutto il2020–2026è già stato visto. Nessun tratto viene etichettato come holdout incontaminato.

## 10. Decisione di ricerca

Con il drawdown lasciato libero in questa fase, **la priorità resta DEDUP_DUAL_TREND_OPP**, perché ha il migliore CAGR BASE della matrice, migliora il confronto con la versione precedente anche con costi doppi e ritardi e mostra un beneficio descrittivo del filtro sullo stesso stato contabile. Non è una raccomandazione di acquisto attuale né una strategia pronta per essere attivata.

Non promuovo il semplice aumento della concentrazione o la media dei portafogli: i controlli hanno già mostrato che possono ridurre il rendimento. La successiva ricerca deve aggiungere informazione utile alla selezione e distinguere il segnale dall'effetto dei prezzi di esecuzione; i modelli di protezione restano un modulo successivo come richiesto. L'obiettivo30% rimane aperto e questa iterazione non lo dichiara raggiunto.

## AppendiceA — Tutte le40configurazioni

DD riportato come perdita negativa; nessun gate di25% nella scelta corrente. ZERO_COST, costi, ordini e tutte le altre metriche sono nel CSV completo; la tabella presenta gli stress economicamente più utili senza omettere configurazioni fallite.

{fulltab}

## AppendiceB — Fonti e riproduzione

Fonti dei risultati: i tre `RUN_MANIFEST.json`, `analysis/ALL_SCORECARD.csv`, `ALL_ANNUAL_RETURNS.csv`, `ALL_SEGMENTS.csv`, `PAIRED_COMPARISONS.csv`, `MATCHED_STATE_INTERVALS.csv`; `validation/COMBINED_QA.json`, `validation/BOOTSTRAP_ANALYSIS_REVIEW.json`, `validation/source_execution/SOURCE_EXECUTION_AUDIT.json`. Il rapporto precedente immutabile è OLC108V3. I protocolli e il cambiamento dell'obiettivo sono in `docs/`.

Le motivazioni metodologiche hanno fonti primarie, ma i risultati dei paper non vengono trasferiti a questa strategia:

1. Moskowitz, Ooi, Pedersen, *Time Series Momentum*,2012: [paper e sintesi degli autori](https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum).
2. Moskowitz, Grinblatt, *Do Industries Explain Momentum?*,1999: [ricerca degli autori](https://www.aqr.com/insights/research/journal-article/do-industries-explain-momentum).
3. Daniel, Moskowitz, *Momentum Crashes*,2014/2016: [NBER](https://www.nber.org/papers/w20439).
4. Blitz, Huij, Martens, *Residual Momentum*,2011: [Erasmus Research](https://repub.eur.nl/pub/22252/).

I paper trattano anche singole azioni, futures, strategie long/short e universi diversi. Non dimostrano che un portafoglio long-only diETF EUR raggiunga30%. Le fonti del repository, con commit e hash, sono raccolte in `research/prior_repo/PRIOR_EVIDENCE_AND_FUSION.md` e `SOURCE_MANIFEST.json`; la diagnosi precedente è in `research/failure_diagnosis/DIAGNOSIS_V3.md`.

Il pacchetto contiene i target, tutti gli ordini, le istruzioni e i NAV, codice finanziario congelato, test, analisi, revisori indipendenti e input necessari. `README_IT.md` spiega come riprodurre senza sovrascrivere i risultati. Nessuna operazione reale, modifica ad automazioni o pubblicazione di repository è stata eseguita.
'''
    report=editorial_spacing(report)
    (root/'RAPPORTO_OLC109_IT.md').write_text(report)
    print('Report words',len(report.split()),'characters',len(report))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('root');a=ap.parse_args();build(a.root)
