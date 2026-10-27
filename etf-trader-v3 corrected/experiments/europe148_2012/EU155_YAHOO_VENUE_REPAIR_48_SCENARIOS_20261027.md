# EU148 bonifica Yahoo alternative venues + EU155 expanded — 27 ottobre 2026

**Primo run GitHub Actions 40565834430 concluso con successo:** originale EU148 lasciato invariato (conservative policy, nessuna sostituzione automatica), download di sette UCITS europei aggiunti -> EU155. Artifact 12762927075, storico completo per tutti gli ISIN.

**Seconda procedura di selezione alternativa** sui candidati e historical source audit locali: sei sostituzioni della **quotazione Yahoo dello stesso ISIN**, non sostituzioni legali di ETF, su criteri prevalenti di minore volume zero e storia. Selezione originale è conservata e reversibile, senza interpolare prezzi o esiti futuri. Selezioni: IE0005042456 IUSZ.DE -> ISFA.AS (1.3% -> 0% vol zero); FR0010150458 XEYX.DE -> E40.PA (33.1% -> 0.6%); LU1650488494 LYQ3.DE -> EM35.MI (21.8% -> 0.4%); LU1650489385 LYQ6.DE -> EM1015.MI (21.0% -> 3.9%); LU1834988609 LTCM.DE -> TELE.PA (12.1% -> 0.4%); LU1834988864 LUTI.DE -> UTI.MI (7.6% -> 0.4%). Alcune cross-venue giornaliere divergono e nessuna quota è certificata tramite market maker/independent NAV. Per la quotazione LYXIB.MC dell'IBEX35 si è esclusa la storia precedente al reale listing 2018-09-20 che Yahoo riporta apparentemente dal 2009.

**7 nuove exposure UCITS Europa**, nessuna selezione per rendimento ex-post: CAC40 FR0007052782 CAC.PA, FTSE MIB IE00B1XNH568 IMIB.MI, IBEX35 FR0010251744 LYXIB.MC, IBEX35 FR0010655746 AMES.DE (listing da 2024), BEL20 FR0000021842 BEL.BR, MSCI Nordic IE00B9MRHC27 XDN0.DE, Swiss SLI DE0005933964 EXI1.DE. Universo totale 155 ISIN, di cui due IBEX sullo stesso sottostante (esclusione di doppia posizione top K nella selezione). DAX/AEX/FTSE100/ATX già presenti nell'EU148 precedente.

**Secondo run simulazione locale completo:** 48 politiche di esecuzione = tre universi (EU148 originale, EU148 six-venue repairs, EU155) × due criteri di liquidità (nessuno / as-of trailing63d ≥90% volume positivo AND median ADV≥50k EUR) × quattro strategie (momentum252, momentum63, Ridge16, Ridge16+MOM252) × Top3/Top5. 101 segnali 2018-2026, 9 vintage annui Ridge, target 21d future excess EXSA percentuale. 10bps each side, EUR, next-open, tutti gli storici e tradability check non-leaking.

### CAGR netto Top5, filtro liquidità di 50k EUR

| Metodo | EU148 congelato | EU148 sei venue migliorati | EU155 |
|---|---:|---:|---:|
| Momentum252 | 8.22% | 8.06% | 8.79% |
| Momentum63 | 3.69% | 4.15% | 3.80% |
| Ridge16 21d signed percent target | 4.96% | 3.16% | 4.79% |
| Ridge16+Momentum252 50/50 | 11.97% | 11.35% | 10.52% |

Mean monthly Spearman Ridge IC EU148 original .0546, repaired .0496, EU155 .0439. Nessun alpha incrementale significativo. Bootstrap paired 6mo annualized log return Ridge+MOM EU155 minus EU148 original -1.31 pp (CI95 [-2.87,+0.28] pp); repaired minus frozen -0.55 pp (CI [-1.61,+0.52]). Historical 2018-2026 known, no untouched holdout.

**Stato:** la raccolta Yahoo e 48 confronti sono conclusi. Bonifica migliora alcuni indici di integrità/liquidità ma NON dimostra crescita di CAGR e NON raggiunge 30%. Fonte OLD EU148 e USA149 B0 non rimpiazzata. USA149 non ritestato in questo ciclo, perché variazione solo di data venue e universo EU. No produzione modificata.

Results and code are bundled with 155 rows hash integrity + raw series and local 48 NAV: file `EU148_EU155_YAHOO_ISIN_QUALITY_AND_48_RETTEST_20261027.zip` in this ChatGPT conversation. Original code in `eu148_yahoo_alt_venue_indices_20261027.py` and local data selection, training, execution, audits included in package. [Primary GitHub Yahoo run](https://github.com/AM1975MA/Test/actions/runs/40565834430).