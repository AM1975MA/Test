# OLC06: delay versus gradual transfer

Read PROTOCOL.md and RESULTS_IT.md before using results. Research only; no trading, no main edits.

Frozen parent445944685c14bfe6cbeb4269319df1933176afe3; original OLC05 checkpoint SHA256bf81a855e127883ac671dced7ac8dcf95fbe3f08a0339afd537c1c19a4ab6d8d. build_engine.py produces exactly the tested engine SHA256a6dbe479353ba8edf7922f564a6e53827b5c74611371c84e803aaf0342703d2e.

## Repository scope
Included here: frozen protocol; input restoration and exact engine generator; common metrics;48-path replay runner; independent daily accounting kernel; delay/accounting unit tests; compact results and verified-summary metadata. The restored dependency supplies24inherited tests. The complete49-test suite, local-probe runner, longer analysis/bootstrap/report scripts, all NAV/ledgers and input dependency are in the downloadable results/checkpoint delivered with the conversation. Do not describe this GitHub folder as the full binary archive.

To reproduce core paths after obtaining the authenticated OLC05 checkpoint:

    python restore_vendor.py /path/OLC05_Transizioni_Checkpoint_20261031.zip
    python -m pytest -q
    python src/run_experiment.py

The repository subset runs41unit tests; the full downloaded package runs49, including8local-probe tests. Restore verifies204source/delivery entries. No fresh market download occurs. Do not load arbitrary unverified pickle inputs.

48paths include32exact reproductions and16newDELAY3configurations, not48newindependent strategies. Main results use the actual next-Open valuation dates, with the final flat row excluded. Fee .001/.003 retains the legacy half-turnover convention and must not be relabeled10/30bp per side.

No predictor was trained and no alternative monthly forecast calendar was refitted. Each of those is an explicit unexecuted next stage. Static same-start five-interval diagnostics are not a compounded trading strategy. Known original data/execution limitations remain.
