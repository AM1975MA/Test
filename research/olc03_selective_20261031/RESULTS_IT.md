# OLC-03: il veto selettivo evita il danno, ma non aggiunge ancora rendimento

31 ottobre 2026. Lotto concluso:92replay USA149/EU165, nessuna strategia promossa. Nessun cambiamento a CL01, pesi o protezioni;72modelli OLC02 riusati senza nuovi fit. Protocollo e0f4a02517dd8a93254dfd487c4f401dd1d351c5 salvato prima dei risultati.

## Risultati 2021-2024

Coefficiente costo legacy0,001, non automaticamente10bp per lato. Confronto principale CL01 capitale50/50, prima azione appresa possibile febbraio2021. Non e' il vecchio39,33%di altra versione/finestra.

| Versione | CAGR EU | MaxDD EU | CAGR USA | MaxDD USA |
|---|---:|---:|---:|---:|
| CL01 50/50 |15,75%|-26,47%|33,68%|-20,15%|
| OLC02 Ridge profilo, veto diretto |20,81%|-26,27%|9,99%|-34,43%|
| Solo guardia supporto/eta', Ridge profilo |21,23%|-26,27%|9,99%|-34,43%|
| Media ricalibrata, Ridge21 |15,75%|-26,47%|33,75%|-20,15%|
| Veto selettivo, Ridge profilo |15,75%|-26,47%|33,68%|-20,15%|

Tutte32le traiettorie UTILITY, incluse HGB e prior alternative, hanno ZEROveti e NAV identica a CL01 sull'intera storia e ai due costi. Astensione riuscita, NON nuova capacita' predittiva. Non si presenta la coincidenza come strategia migliorata.

## Criterio economico

Regole RAW,SUPPORT,MEAN,UTILITY provate per Ridge/HGB e21/profilo, in entrambi i mercati e costi. Il nuovo veto puo' contraddire solo proposte gia' negative per il modello grezzo; manca supporto o informazione=>CL01. Non introduce cash discrezionale o nuovi ticker. Le posizioni detenute restano quelle effettive del conto, non una posizione ideale.

La ricalibrazione usa le previsioni annuali OOS OLC02 per tutte le proposte CL01 complete dei percorsi di riferimento, inclusi candidati non eseguiti. Target maturo strettamente prima del segnale. Ogni mese ha peso totale1. Profilo=media dei vantaggi log21/42/63 e richiede maturazione di tutti. Servono12mesi; si evita estrapolazione oltre score e eta' conosciuti.

Posterior predictive Student da regressione bayesiana lineare a2coefficienti, con likelihood mensile pesata. Prior beta=(0,0),V0=I,alpha=3,beta0=2,scala0,05. Sensibilita'0,025/0,10. La distribuzione include rumore degli esiti e incertezza dei parametri. E' una distribuzione condizionata a modello/ipotesi, non probabilita' di successo certificata.

UTILITY rifiuta se perdita evitata attesa >2*opportunita' persa attesa. Il2:1e'una scelta sperimentale esplicita dell'analista, non preferenza personale dell'utente. Nessun CI-che-esclude-zero o cutoff95%. MEAN usa peso1, senza la prudenza aggiuntiva. Le correzioni del modello non autorizzano a violare le protezioni originali.

## Togliere prudenza non risolve

Al costo0,001, prima2025, MEAN_RIDGE21 fa un solo veto USA e nessuno EU. Le altre3combinazioni MEAN non intervengono. Al costo0,003 MEAN_RIDGE21 fa7veti EU e2USA e peggiora:

| Versione,costo0,003 | CAGR EU | CAGR USA |
|---|---:|---:|
| CL01 |12,96%|30,11%|
| MEAN Ridge21 |8,85%|24,60%|
| MEAN HGB21 |12,96%|27,14%|
| UTILITY |12,96%|30,11%|

Sul2021-luglio2026,a costo0,001, MEAN_RIDGE21 migliora EU18,22%contro16,63%baseline e USA41,26%contro41,20%. La differenza europea nasce da2mantenimenti nel2026. Non viene nascosta, ma a costo0,003 lo stesso confronto e' EU11,61%contro13,81% e USA33,15%contro37,41%: non e' un miglioramento comune robusto ai costi. Il2026e'parziale e gia' studiato.

## Perdite evitate contro opportunita' perse

Sulle proposte CL01 che il Ridge profilo giudica negative, con tutti gli esiti maturati prima2025:8casi EU e18USA. Vantaggio netto medio statico del CAMBIO EU-1,11punti logaritmici, USA+1,73. Rifiutandole, perdita media evitabile EU3,49punti e USA2,49, ma opportunita' media persa EU2,38 e USA4,22. Ogni media include zero nei casi di segno opposto. Sono medie dei vantaggi cumulativi21/42/63, NON punti annui/CAGR, non una sequenza operativa di trade. Pochi mesi e orizzonti sovrapposti limitano l'inferenza.

Gli USA confermano che il vecchio filtro scartava proposte spesso valide. In Europa esistono eccezioni potenzialmente utili, ma non vengono trasformate ex-post in un diverso filtro solo europeo.

## Esempi

31gennaio2022 USA:TUR/KWEB detenuti, propostaURA/USO, stima grezza netta-1,7bp. Il nuovo filtro segueCL01 per insufficiente storiaOOScalibrabile, non per aver previsto il rally. Il vecchio esempio dannoso non viene ripetuto, ma il merito e'l'astensione.

30agosto2024 USA:KWEB/EIRL, propostaKWEB/TAN. Stima grezza-0,41punti log; ricalibrata+2,63; proposta accettata. Vantaggio statico medio degli orizzonti poi osservato+2,35punti. Caso favorevole, non prova generale e non rendimento mensile di portafoglio.

## Qualita' delle probabilita'

La ricalibrazione spesso migliora MSE rispetto al modello grezzo, ma non dimostra sufficiente discriminazione. Copertura empirica degli intervalli predittivi nominali95%:EU86,7-92,9%su28-30osservazioni per modello/orizzonte;USA96,6-100%su26-29. Non vengono chiamate probabilita' ben calibrate per il trading.

Contrasti economici:bootstrap mensile appaiatoUSA/EU3/6mesi,10000estrazioni seed20261031. Frazioni positive non sono posteriori. Un intervallo nullo fra curve identiche descrive zero interventi, non equivalenza futura. Nessuna esclusione automatica per inclusione dellozero.

## Verifiche

526fileparent e32input preparati verificati prima della deserializzazione.720calibrazioni sequenziali, zero nuovi fit dei72modelli diretti.26test nuovi+23parent passati nelle rispettive suite; non e'dichiarata verde tutta la storiaGitHub.92NAVricostruite da posizioni post-stop/prezzi successivi,172914intervalli contabili,errore massimo3,56e-15.3588metriche ricalcolate,errore2,23e-15.28controlli identici ai parent,errorezero.6prove temporali con alterazione di input futuri lasciano invariati passato e decisioni. Self-review dell'autore, non revisione indipendente.

Restano esecuzionelegacyallo stessoOpen,survivorship,total-return/corporateactions/liquidita'non certificati,storia gia'selezionata e domain shift fra traiettorie di riferimento del calibratore e stati endogeni. La statistica non rimuove questi limiti.

## Decisione e conservazione

Non adotto un filtro che non produce azioni aggiuntive utili. Conservo l'astensione come presidio di ricerca, CL01 come baseline, e i rari miglioramenti MEAN come ipotesi non robuste ai costi. Non abbasso soglie per forzare interventi. Il segnale deve diventare migliore nel distinguere deterioramento dell'opportunita' e semplice volatilita', non solo piu'flessibile.

Nel branch sono salvati protocollo,sintesi e nucleo implementativo. I download contengono TUTTE le nuove sorgenti,test,92curve/ledger,decisioni e diagnostica; il checkpoint contiene anche copia autenticata OLC02. I grandi input non sono implicitamente caricati suGitHub. Nessun main/trading modificato.

Source bundle completo consegnato:SOURCE_CODE.tar.xz SHA2564fa6300e7a5be8e8cbfb52cc28b338bfa27cba505c8fd634f73b1d5307893456. Dataset e dettagli nei file SCORECARD.csv,DECISION_COUNTS.csv,SHADOW_SUMMARY.csv,PREDICTIVE_SCORECARD.csv,PAIRED_CONTRASTS.csv,VERIFIED_SUMMARY.json.
