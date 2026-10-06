# Evidence V2 — Macro Context v1 fetch retry fix

Status: **ENGINEERING-ONLY AMENDMENT BEFORE ANY DATASET WAS FROZEN**

Initial workflow run `37068346569` failed during the first network acquisition step with a read timeout from FRED. No macro dataset, model output, metric or result was persisted.

The acquisition code is changed only to:
- request the same preregistered FRED IDs with the preregistered `2005-01-01` to `2026-06-30` date bounds encoded in the URL;
- retry transient download failures up to five times;
- use a longer read timeout.

No series, transformation, coverage gate, causal alignment rule, model design or scientific decision rule changes.