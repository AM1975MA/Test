# Attribuzione dei punteggi alle decisioni europee

Controllo aggiuntivo sul replay gia' eseguito; nessuna modifica, nessun nuovo fitting, nessuna ottimizzazione.

Sul medesimo insieme di candidati con score combinato disponibile, Return-Rank+Hybrid cambia il primo ETF di Hybrid in49dei89mesi e l'insieme dei due ETF in69mesi. Prima del2025 il primo ETF cambia in43mesi su71. Non e' quindi una piccola correzione occasionale del selettore Hybrid.

## Segnale31luglio2024, disponibile prima delle perdite di agosto

| ETF | Posizione Return-Rank | Posizione Hybrid | Posizione finale combinata |
|---|---:|---:|---:|
| QDVE.DE | 2 | 9 | 1 |
| VVSM.DE | 7 | 13 | 2 |
| DXSE.DE | 104 | 2 | 43 |
| EXH9.DE | 133 | 1 | 75 |

La formula congelata e' score_finale=.475*Return_percentile+.525*Hybrid_smoothed_power. Per QDVE contro EXH9, il vantaggio ponderato del Return e' circa+.4174; lo svantaggio ponderato Hybrid circa-.0218. La parte Return domina questo confronto nonostante il suo coefficiente nominale sia inferiore a quello Hybrid. E' un'identita' contabile dei punteggi, non una spiegazione inventata dopo i rendimenti.

## Segnale31ottobre2023

DXSE.DE e EXV4.DE passano rispettivamente dal3 e5 posto Hybrid al1 e2 posto finale. IM2A.DE e EEAA.DE passano dal1 e2 posto Hybrid al8 e10 posto finale. Il Return mette i primi due ETF al2 e3 posto, gli ultimi al29 e33. Nel successivo novembre la selezione combinata rende circa1,56%, Hybrid13,00%, con medesimi pesi/costi/controlli; la differenza non nasce da un veto di rischio.

## Segnale31agosto2022

EEPG.DE passa dal6posto Hybrid al1posto finale; ZPRP.DE dal3al2. EXV5.DE, primo Hybrid, scende al17posto finale; S7XE.DE, secondo Hybrid, scende al7. Il ranking combinato produce la coppia immobiliare osservata nel successivo episodio di perdita.

## Interpretazione circoscritta

La fusione non ha influenza effettiva47,5/52,5 su ogni scelta: dipende dalle differenze e dalla distribuzione dei due score, uno percentile e l'altro smussato/trasformato. Questi casi identificano precisamente il punto in cui vengono ribaltate le scelte. L'eventuale calibrazione delle ampiezze e' una NUOVA ipotesi da testare separatamente negli USA e in Europa, non un miglioramento gia' dimostrato. Non e' ancora dimostrata la causa interna al training per cui Return assegna quei ranking, ne' che ripesare il blend recuperi il39%.

Il pacchetto completo contiene diagnosis/DECISION_SCORE_ATTRIBUTION.csv e SELECTION_DISAGREEMENT.json, con valori continui e ranking per ogni ETF dei tre episodi. I rendimenti successivi sono usati solo nella diagnosi, mai nel calcolo del segnale.
