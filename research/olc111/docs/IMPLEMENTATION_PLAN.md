# OLC111 implementation plan

Authority: `DESIGN_AND_PROTOCOL.md`; prior design memo is advisory where it differs.

1. Strict Cboe as-of adapter and meaningful boundary tests. Owner restore agent.
2. Minimal seeded replay extension with default parity and actual-unit HOLD tests. Owner history agent.
3. Mature date-balanced nested Ridge / paired block-bootstrap adapter and temporal tests. Owner design agent.
4. Root: causal basket features, monthly representative breadth, label-bank builder using seeded native replay, callback policies, frozen run driver and outputs. Test economic labels against hand-computed gap/cost cases and model-policy transitions.
5. Verify input/code/protocol hashes before first run; build labels once, fit once, forecast and18 account paths. Preserve full result ledgers. Evaluate forecast and financial gates without tuning.
6. Independent review for look-ahead, label maturity, no-op/HOLD semantics, missing tails, cost double counting and ablation attribution. Fix concrete important issues with regression tests. Save immutable source/results on research branch with restore instructions; report candidly in Italian.

Dependencies: model consumes (price6/5,legacy2,term2,net advantage,signal_idx,terminal_idx); replay consumes exact baseline units/cash with empty queue; label features and policy use the same feature function. Monthly model readiness is separate per head. Date support is shared across information arms. No code or data from old studies is modified.

The workspace is an isolated new `olc111` directory, not a checkout of main; remote integration uses a new research branch parented to the saved OLC110 commit. User's existing carte blanche and explicit save-to-Test instruction authorize work and branch saving without another permission request.
