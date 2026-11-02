# EXP-RAG-CTP001 fixtures: constraint type C1 (Stage B-1)

Fourteen fixtures of the constraint "Refunds over $500 may be issued only with
manager approval." (type C1, conditional permission). They are the C1 column of the
84 fixtures of `EXP-RAG-CTP001 実験設計書 v0.3` section 5 (6 types x 14 examples).
One file per example: `c1_<example>.json`. They are separate from the existing
`tests/golden/representation_*.json`, which are untouched.

The files are written by `tests/ctp001_c1_builder.py` (`python tests/ctp001_c1_builder.py`
with `PYTHONPATH=src`). `tests/test_ctp001_fixtures.py` checks that each committed
file equals what the builder writes, so the builder is the source of the text.

## Examples

| Example | What it is (v0.3 section 5) |
|---|---|
| G0 | nothing dropped |
| P0 | f1 rewrites the sentence and keeps the meaning |
| D0 | f1 declares the condition lost; every composite claims it preserved |
| B1 | f1 drops the condition (honest `lost`) |
| B2 | f1 changes the modality, `may` to `will` (honest) |
| B3 | f1 changes the number, $500 to $5,000 (honest) |
| B4a | f2's decision does not touch the constraint (honest `lost`) |
| B4b | f2 touches the constraint and contradicts it |
| B5 | the decision is correct, f3's action breaks the constraint |
| B6 | f1 drops the condition but every stage declares `preserved` |
| B7 | f1 drops the condition (honest), the case needs no approval, the action is right |
| X0 | stages declare the condition lost, but every output still has it |
| N0 | `not_applicable` constraint that is dropped (negative control) |
| U0 | `undetermined` constraint that is dropped |

## File fields

| Field | Meaning | v0.3 / v0.2 |
|---|---|---|
| `history` | a `RepresentationHistory.to_dict()`, same format as the existing goldens. Four states K (knowledge), X (context), Y (decision), Z (action); stages f1 K->X, f2 X->Y, f3 Y->Z; six non-identity morphisms (f1, f2, f3, k12, k23, k123) and four compositions, so R2 finds every associativity case defined | v0.3 section 6 G5 |
| `vocabulary` | the three properties `c1.condition`, `c1.modality`, `c1.threshold` (the non-null fields of the schema, `<constraint_id>.<field>`); seal is the fixed value `SEAL_OK` | v0.2 section 4 |
| `chain` | the stage ids in order | v0.3 section 3 |
| `constraint_schema` | the Constraint Schema of c1 | v0.2 section 4 |
| `applicability`, `applicability_basis` | `applicable`, `undetermined` or `not_applicable`; the basis is `fixture` | v0.3 section 2 |
| `obligations` | the Obligation Set `O`: applicable and undetermined constraints' properties; empty for `not_applicable` | v0.3 section 2 |
| `obligation_exclusions` | why a constraint was left out of `O` (N0) | v0.3 section 2 |
| `carry_evidence` | outside the history (v0.3 section 6 G3): per stage and property `{property, status, basis="evidence", source="verifier", evidence_ref}` | v0.2 section 4 |
| `situation` | the case facts used to judge L3 and f3 | v0.3 section 4 |
| `texts` | knowledge, f1 context, f2 decision, f3 action record (English) | v0.1 |
| `note` | how the example was built, one line | - |
| `expected` | see below | v0.3 section 5 |

Declared statuses are in the history (`preserved` / `lost` / `carry` of f1, f2, f3
and of the composites). Evidence statuses are in `carry_evidence`.

## Status convention (an assumption, the design leaves it open)

The status of a property at a stage is whether it is still present in that stage's
output, measured against the knowledge-side Constraint Schema. A property lost at f1
therefore stays `lost` at f2 and f3 (declared and evidence alike), and the texts are
written so that each stage restates what it still has. R9's location is the first
stage with a finding (v0.2 section 5).

## `expected`

| Key | Content | Checked now |
|---|---|---|
| `r1`, `r2` | `PASS` (the target of G5) | yes |
| `r3` | value (the worst of all `CheckResult`s of the rule; v0.3 section 3, report F13) and the set of reason codes | yes |
| `r9.m1`, `r9.m2` | value, reason codes, location (first stage), annotations. M1 = declared only, M2 = declared and evidence. Derived from the v0.3 section 3 table by the builder, and compared with the section 5 table in the test | shape only |
| `compliance` | `L1`, `L2`, `L3`, `f3` and `overall`. L1: the decision touches every field of the obligations. L2: PASS if it is consistent with the constraint, FAIL if it contradicts it, UNVERIFIABLE if it is silent. L3: the situation satisfies the constraint's condition. `overall` is the worst of L2, L3 and f3 (an assumption; v0.3 does not define it) | shape only |
| `two_axis` | `retention` (R9 M2: PASS carried, FAIL lost, UNVERIFIABLE undetermined), `compliance`, `class` (v0.3 section 1) and `undetermined_axes` | shape only |

The content of R9, compliance and the two-axis class is checked once R9 and the
Constraint Verifier exist (Stage C); the test is `pytest.mark.skip` until then.
