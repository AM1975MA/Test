# OLC109 — Blocco adattivo3: orizzonti, capitale e concentrazione

## Obiettivo aggiornato e natura del test

L'utente accetta temporaneamente drawdown superiori e rinvia i modelli di protezione. Vale docs/OBJECTIVE_UPDATE.md: target corrente CAGR30% annuo, drawdown/Calmar misurati ma non usati come gate di selezione. Questo blocco è deciso dopo i160 risultati dei blocchi1/2, incluso25,75%CAGR di DEDUP_DUAL_TREND_OPP, e dopo la revisione del repository. È esplorazione adattiva dichiarata. Nessun risultato di questo blocco è stato calcolato al freeze.

## Ipotesi distinta

Il leader annuale può reagire tardi. Si confrontano leader individuali a63/126/252 sessioni, concentrazione su1 vs3ETF e investimento simultaneo in tre portafogli di orizzonte. La miscela riguarda i pesi di capitale correnti nello stesso conto, non le medie di score o dei CAGR. OLC102 sullo smoothing dei rank non è la stessa architettura. Precedenti test63/126 su piccoli universi non convalidano questo test su2.096 ETF V3.

## Dati, costi e segnali

Stessi dati e motore dei protocolli precedenti, decisioni mensili/nextOpen, tutti5 scenari, EUR10.000, cash0, noleva/short, nessuna uscita extra o controllo di volatilità. Il filtro comune è: liquid_eligible V3 con mediana controvalore63>=EUR100.000 e osservazione corrente; m252>0, m63>0, prezzo>SMA200. Tutti i valori sono noti al Close del segnale. Il filtro di trend è comune ai controlli; non viene ritoccato per un orizzonte.

HORIZON63/126/252: ordinare gli individui per il rispettivo log-rendimento, parità ISIN. Scorrere fino a3nomi, ammettendo al massimo un componente per ciascun gruppo complete-linkage del blocco1 e corr126<=0,85 con tutti i nomi già scelti. Nessun punteggio mediano e nessuna sostituzione con il membro più liquido. Ogni posto pesa1/3; posti vuoti restano cash.

HORIZON63_TOP1/126_TOP1/252_TOP1: stesso insieme idoneo e graduatoria,100% sul primoETF, altrimenti cash. La concentrazione è intenzionale, osservabile e senza leva; i limiti di correlazione tra posizioni non hanno effetto con una sola posizione.

CAPITAL_3H: media aritmetica dei tre vettori di pesi dei portafogli TOP3: (w63+w126+w252)/3. Gli ordini sono compensati nel singolo conto. Titoli ripetuti si aggregano. Il target di ogni gruppo e di ogni coppia con correlazione>0,85 non supera1/3, perché ogni sleeve può contenerne al massimo uno. I target non sono limiti rigidi dei pesi effettivi dopo drift, banda3%, esecuzioni parziali o ritardi.

CAPITAL_3H_TILT: stessa unione dei titoli e stessa esposizione di CAPITAL_3H. Si applica il tilt solo se tutti i3TOP3 sono pieni (gross1 ciascuno); altrimenti pesi dei portafogli1/3. Per ciascuno dei3portafogli si calcolano b=media dei m21 dei suoi3ETF attualmente selezionati e a=media dei precedenti105divisi5; accelerazione=b−a. Sono candidati al sovrappeso soltanto i portafogli con b>0 e accelerazione>0. Se nessuno è candidato,1/3ciascuno. Altrimenti il massimo di accelerazione riceve50%del capitale e gli altri25%; in caso di massimo identico, il bonus25% si divide tra i massimi, aggiunto al25%base di ciascuno. È una statistica storica dei candidati correnti, non la performance reale di un portafoglio posseduto nei21giorni precedenti. Non si ricostruiscono rendimenti retroattivi di portafogli appena scelti.

Essendo una combinazione convessa di portafogli con gli stessi limiti, il tilt mantiene il cap target di gruppo/coppia1/3. Ogni sleeve resta finanziato almeno25%, quindi l'unione dei titoli rimane la stessa. Non viene appreso alcun coefficiente.

## Matrice8×5=40

1. HORIZON63
2. HORIZON126
3. HORIZON252
4. CAPITAL_3H — confronto principale rispetto HORIZON252
5. CAPITAL_3H_TILT — allocazione a titoli e gross invariati rispetto CAPITAL_3H
6. HORIZON63_TOP1
7. HORIZON126_TOP1
8. HORIZON252_TOP1

BASE,ZERO_COST,DOUBLE_COST,LAG1,LAG2 per tutti. Output results_stage3; gli altri160 risultati e hash restano invariati. Totale OLC109:40configurazioni×5scenari=200percorsi.

## Valutazione e limite di questa iterazione

Confronti controllati: stesso numero di posizioni per effetto dell'orizzonte; stesso orizzonte per effetto della concentrazione; CAPITAL_3H vs HORIZON252 per miscela di capitale; TILT vs MIX per allocazione senza cambiare unione dei titoli. Tutti gli anni incluso2024, segmenti2021–24 e2025–26, costi/ritardi, trade participation e audit indipendente. Si separano i percorsi BASE che superano30% dai casi senza costi. Il target non giustifica nuove soglie dopo il risultato. Questo completa il blocco di ricerca della sessione: nessuna ulteriore griglia per inseguire il30% all'interno dello stesso passato.
