# Verifica cinque ISIN justETF vs yfinance — 19 ottobre 2026

**Azioni concluse:** [Primo download 16 ticker](https://github.com/AM1975MA/Test/actions/runs/39308014699) (success) e [Secondo download 4 ticker](https://github.com/AM1975MA/Test/actions/runs/39308432664) (success). Quota identificata su normali schede pubbliche justETF, non scrapping API justETF. Prezzi scaricati soltanto con yfinance 0.2.65. Totale 20 ticker provati, **12 ETF EUR Yahoo scaricati**, 8 senza dati, tutti i 5 ISIN rappresentati.

## Corrispondenze e storico
| ISIN | Sottostante | Ticker Yahoo | Primo giorno | Volume Yahoo zero % feb2017-lug2026 | Avvertenza |
|---|---|---|---|---:|---|
| LU1681042518 | EUROPA MSCI Europe Value | CV9.PA | 2009-02-26 | 14,87 | 17 barre OHLC anomale, 13,54% flat |
| LU1681042518 | EUROPA | VCEU.MI | 2018-04-19 | 12,84 | non copre 2017 |
| LU1900066033 | GLOBALE, ESCLUSO | LSMC.DE | 2024-01-29 | 0,00 | buona quota recente |
| LU1900066033 | GLOBALE, ESCLUSO | CHIP.MI | 2019-02-22 | 11,80 | storico solo da 2019 |
| LU1900066033 | GLOBALE, ESCLUSO | CHIP.PA | 2008-01-02 | 20,56 | 88 barre OHLC errate e ISIN attuale/predecessore non verificato nel 2008 |
| NL0011683594 | GLOBALE, ESCLUSO | TDIV.AS | 2016-05-23 | 0,00 | buona continuità, ma solo circa 175 sedute prima del feb2017 (126 calcolabili) |
| NL0011683594 | GLOBALE, ESCLUSO | VDIV.DE | 2019-01-10 | 8,70 | precedente storico non su Xetra |
| NL0011683594 | GLOBALE, ESCLUSO | TDIV.MI | 2019-04-23 | 19,18 | pessima concordanza ritorni con Amsterdam |
| LU1834987973 | EUROPA Insurance | LIRU.DE | 2024-03-25 | 4,18 | classe quotata Xetra First Trading 2019; Yahoo solo 2024 |
| LU1834987973 | EUROPA Insurance | INS.MI | 2024-04-17 | 1,26 | 121 High-Low envelope violazioni |
| LU1834987973 | EUROPA Insurance | INS.PA | 2024-04-17 | 0,00 | 44 High-Low envelope violazioni |
| IE00B5MTXJ97 | EUROPA Insurance | SC0Y.DE | 2009-07-08 | 26,90 | 22,51% barre flat, dato stale o Yahoo Volume non riportato |

Otto alias provati e senza dati Yahoo: CHIPL.MI, CHIPM.PA, TDIV.PA, TDIV.BR, LYYQ.MI, LYYQ.PA, XIPS.DE, SC0Y.SG. Non affermare che siano fondi delistati; alcuni sono RIC non riconosciuti da Yahoo.

## Concetto fondamentale: same ISIN != same exchange price
Dati Yahoo aggiustati:
- CV9.PA vs VCEU.MI, 2.079 giorni comuni: correlazione dei log ritorni 0,92746, 3,08% giorni con differenza >1%.
- TDIV.AS vs TDIV.MI, 1.825 giorni: correlazione 0,67844, **9,70%** giorni differenza >1%: la quota Milano si discosta molto di più rispetto a Amsterdam.
- INS.PA vs LIRU.DE, 557 giorni: correlazione 0,99387, 0% giorni differenza >1% sui Close; INS.PA ha però 44 High/Low non validi.
- CHIP.PA vs CHIP.MI 1.865 giorni: correlazione 0,9021, 220 giorni con differenza >1%.

**Motivo geografico:** LU1681042518, LU1834987973, IE00B5MTXJ97 hanno indici di sottostante europeo. LU1900066033 investe nel MSCI ACWI semiconduttori globale e NL0011683594 nei mercati sviluppati globali con azioni USA e altri extraeuropei: **esclusi** rigorosamente dal modello europeo.

Il NAV, il prezzo di chiusura di una singola venue, i prezzi aggiustati e il valore di un predecessore di fondo sono oggetti differenti. Non usare 2008-2026 CHIP.PA per affermare esistenza storica del moderno ISIN LU1900066033 senza documento di successione, né 2006 come lancio di LIRU.DE 2017. Tutti i dati Yahoo sono un archivio vendor revisabile, non PIT, e Volume=0 può riflettere assenza di dati vendor anziché operazioni effettive. Nessun backtest o modifica a etf_trader.

## Archivi riproducibili
- Prima serie: directory results, vendor OHLC originale, OHLC aggiustato, ticker×ISIN qualità/valuta/inizio/fine, stesso ISIN più piazze, hash SHA256 e JSON.
- Seconda serie: directory second_pass/results, CSV fonte originale e aggiustata e confronto con i risultati del primo lotto.
- Prova fonte: normali pagine justETF ISIN; controprova Xetra 2026 ufficiale per i ticker .DE.
