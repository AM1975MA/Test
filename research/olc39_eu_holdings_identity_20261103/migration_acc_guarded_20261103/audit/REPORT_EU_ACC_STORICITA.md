# ETF Europa — filtro rigoroso della storicità prima di passare da Dist ad Acc

**Data:** 3 novembre 2026. Audit EU-only sul campione EU165 e sui **27 strumenti effettivamente detenuti da Meteorite EU nel 2021–2024**. Nessun ordine, refit o modifica di `main`, USA149, OLC19 o delle quotazioni.

## Decisione richiesta

Se un ETF ad accumulazione non dispone della propria storia osservata nel pannello, **la conversione non si fa**. Una NAV di lungo periodo del fondo emittente non è la prova che la nuova classe Acc fosse quotata con quel ticker nelle stesse date. Non usare serie artificiali, ETF Dist in fallback retroattivo, aggiustamenti ex post o prezzi ffill come quotazioni eseguibili.

### Soglia volutamente restrittiva

Per un candidato già presente nel pannello originale EU165 di OLC19, pretendiamo almeno:

1. **Prima quotazione Open originale osservata al più tardi il 1 febbraio 2019** (primo giorno del pannello conservato; non si accettano quotazioni del comparto predecessore attribuite alla classe nuova).
2. **Almeno 252 aperture valide anteriori al primo segnale di gennaio 2021**, e almeno il **98%** delle 1.026 sedute registrate nel 2021–2024 con apertura positiva, finita, `observed=True`. Non chiediamo a un ETF di quotare nei giorni di chiusura del suo mercato.
3. **ISIN e classe Acc esistenti realmente** alla data di cui si pretende il prezzo; stesso indice del Dist e nessuna variazione sostanziale di hedging/valuta/mandato; dati issuer storici e liquidità sufficiente. Il criterio sugli Open soddisfa la parte quantitativa, NON certifica da solo index lineage, corporate actions o spread.
4. Il sostituto già presente nell'universo non può essere contato due volte o diventare un ETF diverso con lo stesso ISIN. La prova di ricerca può dunque ridurre il numero di ticker distinti; non deve mai riscrivere le decisioni o il NAV originali.

La scelta conservativa di copertura dal 2019 è più severa del solo `>=252` sedute pre-2021 e serve a non alterare lo storico pieno **febbraio 2019–luglio 2026**. Gli ETF che non superano il gate rimangono invariati anche nei periodi successivi.

## Per i nove ETF a distribuzione realmente detenuti 2021–2024

| Dist originale | Acc candidato | Esito | Motivazione |
|---|---|---|---|
| `EXV5.DE` automotive | `EXHG.DE` (DE000A2QP4A8) | **NON convertire** | Classe Acc lanciata **06/04/2022**; impossibile coprire 2019–2021. |
| `EXV3.DE` tecnologia EU | `STEC` (DE000A2QP398) | **NON convertire** | Classe Acc lanciata **06/04/2022**. |
| `EXX1.DE` banche euro | `EXI4` (DE000A2QP372) | **NON convertire** | Classe Acc lanciata **03/12/2021**. Nelle risposte precedenti il ticker `EXA1.AS` era errato; per l'ISIN indicato, la classe è `EXI4`. |
| `EXV6.DE` risorse di base | `LBRE.DE` (LU1834983550) | **NON convertire** | Classe/quotazione Xetra avviata nel **marzo 2024** (prima Open source osservata 25/04/2024), anche se fondo predecessore riporta 2006. |
| `EXV1.DE` banche Europa | `LBNK.DE` (LU1834983477) | **NON convertire** | Classe/quotazione Xetra dal **marzo 2024** (prima Open source osservata 25/03/2024); non ereditare automaticamente la NAV 2006. |
| `EXV9.DE` viaggi | nessuno verificato | **NON convertire** | Nessun Acc same-index con propria storia completa e quotazioni verificate. |
| `EXI5.DE` immobiliare Europa | nessuno equivalente | **NON convertire** | I comparabili Acc disponibili replicano indici/aree differenti. |
| `EXH1.DE` petrolio e gas | nessuno verificato | **NON convertire** | Assenza di sostituto same-index dimostrato con storico valido. |
| `IM2A.DE` immobiliare eurozona | **`EEAA.DE` (LU0950381748)** | **Solo candidato per ricerca** | Classe Acc nata **08/07/2013**, 502 Open osservati prima del segnale gennaio 2021 e **1.021/1.026** nel 2021–2024 (99,51%). Medesimo benchmark FTSE EPRA/NAREIT Eurozone Capped secondo le schede attuali; necessaria convalida PIT/total-return prima di applicarla. |

**Sintesi audit 27 holdings:** 9 a distribuzione; **5 candidati respinti per storia insufficiente**, 3 senza un Acc equivalente verificato, **1 solo candidato con storia dei prezzi sufficiente**. Gli altri 18 detenuti risultano Acc nella classificazione corrente, ma ciò non certifica le composizioni storiche.

**Effetto sull'universo:** `EEAA.DE` è **già** nell'EU165: togliere la duplicazione economica `IM2A.DE → EEAA.DE` lascia **164 ticker distinti** in una possibile copia di ricerca. Non è corretto duplicare EEAA in una lista da 165 e addestrare il ranker come se fossero due opportunità. Il file `EU_ACC_RESEARCH_UNIVERSE_NOT_APPLIED.csv` registra questa ipotesi NON applicata. È obbligatorio rigenerare/testare i modelli se si desidera davvero utilizzare l'universo da 164: il vecchio 23,20% EU e 50,77% USA NON cambia per effetto del solo mapping.

**Perimetro non ancora certificato:** gli altri **138 ETF EU165 che non compaiono nei 27 detenuti** non sono stati classificati strumento per strumento nella presente verifica. Nessuna dichiarazione di avere convertito *tutti* gli EU165. Mantenere invariata la lista originale finché l'intero universo non è verificato. La fonte delle quotazioni originali ha `observed`, ma non prova total-return, dividend reinvestment, qualità intraday/asta, liquidity/spread o survivorship.

## Fonti esterne e dati tecnici

- iShares/justETF automotive Acc EXHG DE000A2QP4A8 (lancio 2022): https://www.justetf.com/it/etf-profile.html?isin=DE000A2QP4A8
- iShares Technology Acc STEC DE000A2QP398 (lancio 2022): https://www.blackrock.com/it/consulenti/products/326632/ishares-stoxx-europe-600-technology-ucits-etf-de
- iShares Banks Acc EXI4 DE000A2QP372 (lancio 2021): https://www.justetf.com/it/etf-profile.html?isin=DE000A2QP372
- Amundi Banks Acc LBNK LU1834983477 (listing 2024): https://www.amundietf.lu/en/individual/products/equity/amundi-stoxx-europe-600-banks-ucits-etf-acc/lu1834983477
- Amundi Basic Resources Acc LBRE LU1834983550 (listing 2024): https://www.amundietf.lu/en/individual/products/equity/amundi-stoxx-europe-600-basic-resources-ucits-etf-acc/lu1834983550
- BNP Easy EEAA Acc LU0950381748 (lancio 2013): https://www.bnpparibas-am.com/en-lu/fundsheet/equity/bnp-paribas-easy-ftse-epra-nareit-eurozone-capped-ucits-etf-c-lu0950381748/
- BNP Easy IM2A Dist LU0192223062: https://etf.money.it/etf/bnp-paribas-easy-ftse-epranareit-eurozone-capped-LU0192223062
- Quote e maschere: `OLC38_MINIMAL_EU_SOURCE.zip`, SHA256 `6b4d59814dfeaab8fac415498755cdad664e76b20a424eb0e0aac6568a771f8d`, stato `EU_STATE_HALF.npz` con 1.898 date dal 2019-02-01, 167 strumenti inclusi i due cash tecnici; universo investibile EU165.

**Decisione finale:** solo la mappatura `IM2A → EEAA` supera il controllo quantitativo di storicità per il sottinsieme già studiato; **non viene attivata automaticamente**. Tutti gli altri rimangono Dist; USA e modelli originali congelati. Prima di ogni eventuale conversione investibile, completare classificazione di tutto EU165, controllo di payout/indice PIT e un replay realmente matched con rischi, V6, commissioni e dati corretti.
