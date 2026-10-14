# Correzione condizionale alle feature — discussione durante l'attesa

14 ottobre2026. Nessun nuovo test oltre BUDGET300 e LINEAR.

L'audit dei90 checkpoint originali misura, nelle validazioni dei singoli semi,
KL media1,168603 contro1,255793 della distribuzione uniforme; percentile Top1
medio0,506331, frequenza nel miglior decile28,1549% e nel peggiore26,9852%.
Ogni checkpoint media le proprie date e i90 checkpoint sono equiponderati.
Questi numeri non descrivono l'ensemble fuori campione né il portafoglio V2.

La cross-entropy ListNet mira alla distribuzione q=softmax(label/T), non al
rendimento atteso. Nel caso predittivo senza vincoli, l'ottimo della loss
attesa è E[q|X]; la rete condivisa per ETF può solo approssimarlo nella famiglia
consentita. L'esponenziale può valorizzare frequenti estremi superiori anche
quando esistono frequenti estremi inferiori. Il denominatore della query
impedisce di applicare ingenuamente Jensen a un rapporto di aspettative.
Questa è una spiegazione possibile, non una causa dimostrata dai risultati.

Gli agenti ML e finanziario hanno confrontato due correzioni:

1. Un correttore dell'utilità condizionato a feature disponibili, score e soli
   errori maturi. È un nuovo metamodello; richiede residui da previsioni
   realmente fuori campione temporale e split/purge anche per il correttore.
   Una funzione comune strettamente crescente degli score conserva l'ordine;
   una correzione condizionale può cambiare i leader. Minore errore non prova
   maggiore CAGR né minore drawdown del percorso.
2. Un'analisi della sensibilità dello score rispetto agli errori degli input:
   localmente var(delta score)=gradiente' Sigma gradiente. Per Top1 conta
   soprattutto la varianza del margine fra ETF, incluse covarianze incrociate.
   Tre acquisizioni correlate non stimano liberamente una covarianza125×125:
   per una stessa osservazione il rango empirico è al massimo2. Non confondere
   incertezza numerica con rischio finanziario e non promettere garanzie.

## Confronto con ciò che è già stato provato

- NF_A: residuo EWMA per ticker di .6 ET_TAIL+.4 XGB_TAIL rispetto al target63.
  MAE ridotta6,25%, span CAGR4,92→9,19pp; non era correzione di Compact21/ListNet.
- NF_B: affidabilità storica63 e inerzia dei ranghi Stage19; span9,53pp e qualità
  peggiore. NF_C: affidabilità63 sulla sola esposizione, leader invariati;
  span4,92→4,85pp, riduzione1,56%, insufficiente al gate.
- Il correttore residuale appreso era già una proposta rinviata in
  forensics_v1/STATUS_AND_NEXT.md; altre famiglie di reranking a feature esistono.
  Non presentare l'uso delle feature come novità assoluta.

Non risulta eseguita la precisa combinazione di score ListNet21 e correttore
condizionale appreso su vere OOF, ma serve un controllo di non duplicazione
completo prima di un eventuale protocollo. Gli attuali checkpoint annuali non
forniscono automaticamente OOF anteriori al2017. Usare gli stessi residui per
correggere e valutare ricreerebbe contaminazione del test.

La domanda successiva sarebbe se una componente dell'errore sia prevedibile
prima dell'esito e persistente nei periodi successivi. Non è una conclusione
già ottenuta. Prima terminano i due controlli preregistrati in corso.
