# OLC114 progress — 16 November 2026

## Authority and isolation

User authorizes autonomous ETF strategy research, implementation, testing and saving to AM1975MA/Test. No new permission pause is needed. Old studies are read-only; new olc114 directory and a later dedicated research branch isolate work. There is no local Git checkout, so no unrelated repository or worktree was initialized.

## Protocol status

Protocol and plan precede all OLC114 market-data labels, models and account returns. TREE_CYCLE is primary; mean and Ridge are comparators. Five accounts and three scenarios: 15 paths. No parameter grid. Rulings: bootstrap blocks use absolute signal_idx//63; paired occupied-block draws; mature terminal must equal signal+42; nonoverlap means disjoint return increments; portable tree prediction matches sklearn float32 conversion.

## Implementation

- Task1 engine/core/features/bank implemented; 25 synthetic tests passed. Final independent review pending.
- Task2 portable models implemented; 13 synthetic tests passed. Final independent review pending.
- Root integration runner and integration tests in progress.
- Causal selection order reconstruction authorized before bank freeze; not a label or return experiment.
- No OLC114 market-data labels, historical fitted models or account return paths yet.

## Parallel work ruling

The developer requires independent tasks to be delegated when useful. Core and model implementation use separate files and an explicit API contract. Root integrates; a separate reviewer checks accounting/causality. This bounded parallel split is compatible with user carte blanche and takes precedence over a generic sequential skill preference.

## Gates remaining

1. Independent prebank review and source/inputs BANK_FREEZE.
2. Build paired 42-session bank and reconcile BASE endpoints.
3. Integration review, tests and EXPERIMENT_FREEZE.
4. Monthly mature-only fits, 15 complete paths, independent numerical audit.
5. Italian report and verified Git save.

## Prebank gate passed

Independent review found no Critical/Important core/model defects; six adversarial synthetic checks passed. Causal order reconstructed for1970dates and2096ISIN, exact weights matched. BANK_FREEZE written before the first label. Root integration RED8→GREEN8; integration review proceeds while the sealed bank is built.

## Bank completed and reconciled

1698starting dates:1579OK,78scheduled states,41rightedge;3158rows in each head. No missing/stale group censor. Every BASE endpoint matches the frozen full account, maximum difference2.1827872842550278e-11EUR. Root independently verified event hashes, exact event-to-NPZ features/labels, finite values and42-session horizons. The long tool process ended after1326persisted events; an unchanged-freeze resume completed the remaining dates, without rerunning completed groups.

## Experiment gate passed

Independent runner review found no Critical/Important findings for the declared populated-bank experiment. Nine integration tests pass; source SHA38889e0099ec4f19d1fdcad483bf570e1012a45069b2b266e537690cd23dfadf. EXPERIMENT_FREEZE seals the complete bank and runner before any historical fit or account path. Starting the predeclared15paths without changing any plan, feature, model or selection parameter.

## All 15 account paths completed

Monthly fits completed under the frozen source and input identities. Both heads first have sufficient training at843 (1 June2022); protocol activation remains865 (1 July2022), so common returns start866 (4 July2022). All four normal/double-cost BASE/STATIC controls exactly reproduce their old daily and order ledgers.

Primary TREE: full CAGR23.4912916%, sampledDD-36.1035644%; common CAGR21.4033591%, sampledDD-27.2365351%. Against BASE: +0.9204841pp full CAGR, +1.3912251pp common CAGR and +9.2776992pp common drawdown improvement. The full drawdown is the pre-activation2020 episode. The+3pp/no-worseDD material criterion and30%aspiration fail. Positive relative CAGR and common-DD directions persist under both cost and execution-delay stresses.

Mean control takes no plans; Ridge makes50primaryplans and has lower primary/doubled-cost CAGR. TREE makes10primaryplans (7PARK,3REDEPLOY). TREE forecast MSE is worse than MEAN for both heads; positive-buffer REDEPLOY labels have negative realized mean with only3 nonoverlapping42-session intervals. Re-entry skill is not established.

Independent result audit is finishing target/order reconciliation and the complete artifact/source manifests. No frozen financial source, fitted model, input or path has changed after the run.

## Final verification complete

Final independent run:9/9 audit groups pass, all15paths reconciled, 48,953held-asset closes with zero unsupported/stale marks. Maximum accountNAVerror1.31e-10EUR; maximum metricdifference4.44e-16. Independent reviewer closed target-sizing/full-sale/instruction-attribution auditor boundary fixes; no financial input, model or path changed. All305source and12stableoutput hashes verified by auditor. Root fresh complete suite:66/66tests pass. Root also reloaded all81fit files/318portablemodels under a fitting sentinel (zero refits), checked15pathreceipts and exactreadiness.

Italian report and common/full figures complete; root visually inspected the common-period figure. OLC113 already saved at3fb4b44141bfe18cf8dde771a63e0686d400bdec. OLC114 finalGitarchive is the remaining delivery step.

## Final research delivery

The complete study is archived on `research/olc114-position-cycles-20261116` in `AM1975MA/Test`, preserving the OLC113 parent and all prior studies. The external `.olc114_publish/SAVE_RECEIPT.json` records the final commit, complete remote path/mode/blob verification, unchanged prior refs and delivery URLs. No additional model fit or financial path was run during archival.
