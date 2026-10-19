# Perché F3/H1/H3 EU48 rendono meno del previsto? Audit delle opportunità, 19-10-2026

**Verdetto:** Solo parzialmente per natura dell'universo. Le azioni Europa nel paniere hanno offerto ritorni +11–13% annui nella finestra effettiva, mentre H1 +7.89%, F3 +3.51%, H3 +5.65%, F3/H1 +6.05%; modelli e allocazione non sfruttano sistematicamente la componente azionaria vincente. **Ha inciso la combinazione di 13/48 fondi governativi e immobiliari** (7 titoli governativi Euro e 6 property, tutti penalizzati da 2021 a luglio 2026), ma il risultato H1 resta inferiore al MSCI Europe buy-hold. Nessuna prova di alpha statisticamente stabile.

## Prove indipendenti dal training, usando soltanto i 48 ISIN originali, 65 mesi 2021-01-29..2026-07-01
Verifica completata: [GitHub Action 39315587757](https://github.com/AM1975MA/Test/actions/runs/39315587757), SUCCESS, checksums SHA, dati e codice nello stesso branch isolato. Il test usa date di acquisto Open 2021-02-01 e ultimo Open 2026-07-01 (1,331 comuni), stesso motore cash-funded e commissioni 10bps in acquisto/vendita lordi dei test EU48, senza cambiare la matrice fonte.

| Investimento passivo per poter quantificare l'opportunità | CAGR netto | MaxDD giornaliero Open |
|---|---:|---:|
| MSCI Europe 100% (IMEU.AS) buy-hold | **+12.6578%** | -19.0447% |
| Equal-weight 12 ETF equity ampio + country + factor, mensile | **+13.1885%** | -22.2777% |
| Equal-weight 23 ETF settoriali Europa, mensile | **+11.1733%** | -21.3327% |
| Equal-weight 48 ETF, mensile | +8.2419% | -24.1889% |
| Equal-weight 25 ETF NON settoriali | +5.5664% | -27.1549% |
| Equal-weight 7 governativi Euro, mensile | **-1.9363%** | -20.0311% |
| Equal-weight 6 property Europa, mensile | **-1.1259%** | **-47.0725%** |
| EUNH Govt EUR buyhold | -2.4589% | -22.0589% |
| F3 EU48 fresh model | +3.5109% | -24.8650% |
| H1 EU48 fresh model | +7.8922% | -21.8145% |
| H3 EU48 fresh model | +5.6467% | -31.0504% |
| F3/H1 50/50 fresh | +6.0512% | -19.6964% |
| R_H old60→ISIN48 control historical scores (non refit) | +7.1452% | -27.5941% |
| PASSIVE 60% MSCI Europe/40% govt Eur (same monthly trade rules) | +6.5008% | -18.4484% |

Le passività equity 100% hanno rischi azionari maggiori di un 60/40 e non costituiscono lo stesso benchmark di obiettivo/risk limit; tuttavia H1 maxDD -21.81% peggiore del MSCI Europe -19.04% e CAGR più basso, quindi la giustificazione 'è Europa, rende poco' non tiene. La categoria sector è equal-weight *fra ETF* e non fra titoli underlying; esistono rischi di sovrapposizione di posizioni a livello azionario, benché gli ISIN ETF siano unici.

## Rendimenti realmente disponibili dei fondi, senza selezione al mese
48 buy-and-hold individuali 2021-02-01–2026-07-01, un acquisto initiale fee 10bps:
- CAGR media 7.9340%, mediana 7.8775%; 10° percentile -1.7041%, 90° +18.2898%; min -7.7009%, max +34.3366%.
- 21/48 fondi hanno reso **oltre +10%** CAGR; 7/48 oltre +15%, 4/48 oltre +20%; 12/48 negativi.
- GROUP B&H mediane: broad Europa +12.5675%; country +12.9599%; equity factor +9.9038%; sector +9.6234%; immobiliari -1.4862%; governativi -2.3797%.
- Miglior ETF storico EXV1.DE iShares STOXX Europe 600 Banks **+34.3366%** CAGR; SPYZ.DE European Financials **+23.9846%**; XS7R.DE Xtrackers MSCI Europe Financials **+23.9708%**; SXRY.DE iShares FTSE MIB Italia **+22.5243%**; EXH1.DE STOXX Europe Oil and Gas **+18.5609%**; EXH5.DE Europe Insurance **+18.1736%**. Questi risultati sono **conosciuti a posteriori** e NON costituiscono una scelta investibile già nota nel 2021. Diversi ETF sul finanziario detengono società comuni nonostante ISIN differenti.
- Peggior fondo governativo lungo IBCL.DE -7.7009% CAGR. Tra immobiliari EXI5.DE -1.7962%. Nessun fondo property del nostro campione supera zero CAGR individuale da 2021 a 2026.

## Il modello sovra-pesa regioni economiche deboli e non ha ranking affidabile
Governativi+property pesano **13/48=27.08% del numero di fondi** nel basket. Dai pesi mensili costed realmente selezionati:
- F3 **40.92%** quota media investita in governativi/immobiliari, mentre la categoria ha dato CAGR -1%/-2% passivo; dunque overweight di ~13.8 punti percentuali vs universo equiponderato.
- H1 **28.31%**, H3 27.69%, F3/H1 34.62%, R_H 17.69%.
- Nel **primo mese 2021 F3 mette 4 ETF property nei 5 Top5**. Questo NON è un giudizio di un singolo mese sufficiente a valutare F3, ma un esempio corretto di ranking diversamente direzionato.
- Su 65 mesi, vantaggio medio mensile del *paniere selezionato*, prima dei costi, vs random/all48 pari al log ritorno medio:
  - F3 **-0.1908% al mese** (bootstrap 95% [-0.9188%,+0.4928%]).
  - H1 **+0.1110% mese** ([-0.4973%,+0.6651%]).
  - H3 **-0.0539% mese** ([-0.5631%,+0.4087%]).
  - Blend F3/H1 **-0.0399% mese** ([-0.4926%,+0.4097%]).
  - R_H 60→48 **+0.0708%** mese ([-0.5978%,+0.7504%]).
  Nessuno scarto è significativamente positivo. Sono ritorni log pesati nell'intervallo Open→Open, non CAGR annuali, non comprendono il costo di ribilanciamento e possono avere differenze rispetto al portafoglio composto per effetto del rebalancing.

## Quanto si posizionano rispetto a selettori senza informazione?
300 random Top5 mensili con un ISIN diverso per fondo, 10bps cash-funded come modelli, seed fisso 20261019: mediana CAGR **+5.6805%**, 10° percentile +2.9744%, 90° percentile +8.5141%. Percentili F3 16.3°, H1 82.0°, H3 49.3°, blend 57.0°. Il random non ha previsioni e le 300 simulazioni sono uno scenario, NON CI formale di significatività e possono comunque selezionare fondi 2026-survivors con lookahead sul roster.

## Quanto era l'opportunità teorica ex post?
La media dei 5 migliori ETF **conoscendo in anticipo** il ritorno del mese batte l'equal48 di +5.2367 punti LOG **ogni mese** in media, con median cross-sectional return std 2.9943% al mese. L'oracolo con esatte quotazioni Open future cresce del 98.10% CAGR costed nel nostro esperimento: **questo dato è matematicamente una selezione con futuro già conosciuto, assolutamente NON negoziabile, NON segnale reale e NON target sensato da perseguire**; non deve essere confrontato come promessa di rendimento. Dimostra soltanto che la cross-section presenta dispersione fra asset e non è un periodo con 'assenza di vincitori'.

## Conclusione e interpretazione causale corretta
1. La struttura europea priva di global tech / mega cap USA / EM / commodity giustifica un potenziale diverso da USA149. Non giustifica che F3/H1 facciano meno di buy-hold azionario europeo e di una semplice equal-weight dei settori nel medesimo periodo.
2. Il **F3 sovrappesa persistentemente gruppi deboli**, con skill di selezione log meno forte di un baseline pari-peso. Tra settore vs settore non mostra Spearman positivo (rapporto EU48 origin F3 -0.0056 con CI 95% che include zero).
3. H1 è modestamente sopra random Top5 (~82° percentil) ma non stabilmente significativo, e molto sotto asset policy buyhold equity. Regressione fattoriale H1 ha MSE superiore alla media fattoriale storica.
4. Prima di 'cambiare ETF per fare +20%' occorre separare **regole di allocazione tra classi di attivo** da **ranking dei singoli ETF entro ciascuna classe**; un filtro statico solo equity rende +11–13% nel periodo, ma scegliere filtro a posteriori NON è una strategia validata. Eseguire ablazione fissando quote equity/sovereign/property **solo in modo as-of ex ante**, e mantenere le quote di bucket costanti nelle varianti. Inoltre creare denominatore di opportunità matched EU equity-only vs US equity-only sugli stessi periodi.
5. È ricerca ex post su ETF del roster sopravvissuto nel 2026 e prezzi Yahoo corretti retroattivamente, con controlli A/B 2017–26 fissati dopo aver osservato anomalie. Serve universo 2017 PIT e reali spread/quote broker; niente strumento certificato per trading. Non attribuire tutto alla geografia né tutto alla macchina, perché la selezione di un universo esclusivamente europeo condiziona entrambi.

## Archivi
Results JSON, buy&hold ticker 48, forward selected ranking by month, actual bucket exposure, per-month winner cross-sectional opportunities, monthly-true ETF cash costed passive, 300 random-seed outcomes, impossible oracle, source SHA manifest. Nessun codice produzione modificato.
