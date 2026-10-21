# V3 L00 — verifica qualità feature corrette e congelamento della baseline di ricerca

Data: 21 ottobre 2026. **Audit completato con successo.** L00 congelato per l'esperimento isolato L01, senza alcuna rivendicazione di superiorità predittiva rispetto a V2.

## Evidenze dal dataset congelato originale

- [GitHub Actions audit 39652313100](https://github.com/AM1975MA/Test/actions/runs/39652313100), risultato `v3-l00-203-feature-quality`, artifact **12370218044**.
- 149 ETF originali, 187 date mensili di feature dal 2011, **203 colonne** (125 Compact, 60 Tail, 18 ausiliarie).
- **0 violazioni OHLC materiali** con tolleranza 1e−8; 893 disuguaglianze di floating point del tutto trascurabili (solo flag da confronto senza tolleranza).
- 497 volumi pari a zero (non negativi; il loader rifiuta volume negativo). Sono osservazioni reali da trattare come zero, NON righe price-missing da interpolare.
- 15 gruppi duplicati esatti **solo** fra le 60 colonne Tail: molti alias di identiche misure. La deduplicazione sarà un test isolato di L02, non un cambio silenzioso al ranker.
- Cross-sectional robust MAD zero in 9 mesi per `drawdown21_dev` e 1 mese per `drawdown63_dev`: il valore della statistica è indeterminato; manterlo mancante e valutare il fallback esplicito separatamente, senza imputazioni inconsapevoli.
- `log_adv63`, `amihud21/63`: prezzi storicamente adjusted moltiplicati per volume rappresentano un **proxy**, non un turnover in dollari non aggiustato.
- Nessuna feature interamente mancante. I dati mancanti sono differenziati per anzianità dell'ETF; non riempiti retroattivamente.

## L00 decisione

Congelata per i test L01 la rappresentazione **125 Compact matematicamente corrette**, codice `etf-trader-v3 corrected/src/etf_trader_v3/source_only/kernel.py` già copiato in V3. Non si toccano nomi, formule, date, universo o eligibility durante test della loss o della capacità del ranker.

Questo gate certifica **integrità e auditabilità delle feature**, non il miglior modello. I test di vecchi duplicati Tail, MAD=0 e specifiche sull'OHLCV resteranno backlog e verranno isolati prima della promozione del layer di competenza interessato.

## Regole

Nessun CAGR per selezionare L00/L01; usare test causali, Top1/Top3, nDCG@3, regret e IC per L01, senza attivare macro, Tail o risk overlay. OOS 2018–2026 è storico già esplorato, per cui i risultati non saranno dichiarati holdout vergine.
