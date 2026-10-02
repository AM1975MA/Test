# Evidence V2 Results Registry

Evidence V2 is closed. Original149 is a burned development set; Holdout70 is diagnostic/burned and never promotion evidence.

| Test | Run | Status | Top1 | Top5 | Top10 | Top1 CAGR proxy | Durable result |
|---|---:|---|---:|---:|---:|---:|---|
| Frozen LTR comparator | — | reference | 10/114 | 32/114 | 47/114 | 22.0631% | `evidence_v1/checkpoints/retriever_ltr_v1/` |
| V2.1 macro context | 37069663860 | REJECT | 10/114 | 32/114 | 53/114 | 13.8482% | `evidence_v2/results/retriever_macro_context_v1/` |
| V2.2 semantic category context | 37071806933 | REJECT | 8/114 | 38/114 | 55/114 | 12.2115% | `evidence_v2/results/retriever_category_context_v1/` |
| V2.3 calendar context | 37072192617 | REJECT | 8/114 | 31/114 | 55/114 | 17.5129% | `evidence_v2/results/retriever_calendar_context_v1/` |

## Gate

Every V2 candidate had to satisfy all four preregistered conditions on the same 114 Original149 development dates:
1. Top5 > 32;
2. Top10 > 47;
3. Top1 >= 10;
4. Top1 CAGR proxy >= 22.0630708412%.

No V2 candidate passed all four conditions.

## Frozen provenance

### V2.1 macro context
- valid run: `37069663860`
- result path: `evidence_v2/results/retriever_macro_context_v1/`
- macro data freeze run: `37069091858`
- frozen macro daily SHA256: `a07b47d11784e5895fbd59f4a416671d6708f06bd12619b963a5b6c83f1d0474`

### V2.2 semantic category context
- valid run: `37071806933`
- result path: `evidence_v2/results/retriever_category_context_v1/`
- artifact id: `11254929144`
- artifact SHA256: `07aa9d0046cfaa4b506b429a5ccf332785f68c1b15b2a1c89e600a94b54c59a5`
- source Git blob: `7a32cc2110502663669ada745accc6d927d773b9`
- preregistration Git blob: `beab03cc0392fcad16665ff6f2747d40fb23582d`

### V2.3 calendar context
- valid run: `37072192617`
- result path: `evidence_v2/results/retriever_calendar_context_v1/`
- artifact id: `11255195341`
- artifact SHA256: `419d86485e3d0d27c357506d68227c04604ca1ea1888035618afc1354ce0cc44`
- source Git blob: `281c818470371335e4ded038adc7e93c502b82c4`
- preregistration Git blob: `5d9e6138ae2f187d5060f03777dc8be96b929a91`

## Decision

Evidence V2 development on Original149 is closed by the preregistered V2.3 stop rule. No category variants, macro variants, calendar variants, nearby model tuning, or additional information-block tests are permitted on Original149. No Holdout-B is opened because no V2 candidate passed the development gate.
