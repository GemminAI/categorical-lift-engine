# Migration: old forms to the canonical form (Constraint Schema v0.6)

Section 10 of `Constraint Schema 仕様 v0.6`, which keeps the rows of v0.4 and v0.5
section 10 and adds its own; the Source column says which version each row is from.
The same tables in a machine-readable
form are in `migration_map.json`; both are written by `tests/ctp001_v2_builder.py` and
`tests/test_ctp001_v2_fixtures.py` checks that they are what the builder writes, that
every old form the 84 old fixtures hold is a row below, and that nothing is missing in
either direction.

Old fixtures: `tests/golden/ctp001/` (the obligation is a property
`<constraint_id>.<field>`). New fixtures: this directory (the obligation is a Graph
Path, identified by `path_id`; `path_label` is for display only).
`schema_graph_version` is `"1"`.

## Old names and types to the canonical form

"In the old fixtures" says whether the 84 old fixtures still hold the old form.

| Old form | Canonical form | In the old fixtures | Source |
|---|---|---|---|
| `cmp` (v0.3 section 3) | `comparator` | no | v0.4 section 10 |
| field `order` (v0.1 section 1) | field `ordering`, template `T.ordering` | yes | v0.4 section 10 |
| kind `order` (v0.1) | kind `ordering` | no | v0.4 section 10 |
| `path_label` `c4.order` (old property name) | `path_label` `c4.ordering` | yes | v0.4 section 10 |
| kind `exception_rule` (v0.1) | kind `exception` | no | v0.4 section 10 |
| field `exception` is a string | `{exempt}` | yes | v0.4 section 10 |
| `threshold.value` is a number | a decimal string | yes | v0.4 section 10 |
| `threshold` without `quantity` | `quantity` is added | yes | v0.4 section 10 |
| `modality` `"must not"` | `must_not` | yes | v0.4 section 10 |
| `T.ordering` components spelled differently in v0.3 and v0.3.1 | `action`, `after`, `after_edge` | no | v0.4 section 10 |
| `T.exception` components `exempt` only (v0.3) | `exempt`, `except_edge` | no | v0.4 section 10 |
| old property names (`c1.condition`, ...) | `path_id` (identity), `path_label` (display); table below | yes | v0.4 section 10 |
| no link from threshold quantity to ordering event (v0.4 and before) | `threshold.applies_to` is `"ordering.after"` | yes | v0.5 section 10 |
| no `subject` in the constraint (v0.5 and before) | `subject` is added | yes | v0.6 section 10 |
| schema key `kind` (old fixtures) | `constraint_kind` | yes | v0.4 section 2 (not a row of section 10) |

## Templates and their required components

| Template | Components | Granularity against the old property |
|---|---|---|
| `T.condition` | `condition` | same |
| `T.scope` | `scope` | same |
| `T.modality` | `modality` | same |
| `T.threshold` | `quantity`, `value`, `unit`, `comparator` | changed |
| `T.exception` | `exempt`, `except_edge` | same |
| `T.ordering` | `action`, `after`, `after_edge` | changed |

"same": the old property and the new path are the same unit, so the result of R9 on
the old property and on the path must agree (step 6, not done here). "changed": the
old property is one unit, the path is a structure of several components
(`T.threshold`: quantity, value, unit, comparator; `T.ordering`: action, after and the
direction of the AFTER edge), so an example may differ (step 6, not done here).
`T.exception` gains `except_edge` in v0.4; its unit is still one property, so it stays
"same".

## Old property to new path

| Old property | New path (label) | Template | Granularity |
|---|---|---|---|
| `c1.condition` | `c1.condition` | `T.condition` | same |
| `c1.modality` | `c1.modality` | `T.modality` | same |
| `c1.threshold` | `c1.threshold` | `T.threshold` | changed |
| `c2.modality` | `c2.modality` | `T.modality` | same |
| `c2.scope` | `c2.scope` | `T.scope` | same |
| `c3.modality` | `c3.modality` | `T.modality` | same |
| `c3.threshold` | `c3.threshold` | `T.threshold` | changed |
| `c4.order` | `c4.ordering` | `T.ordering` | changed |
| `c4.threshold` | `c4.threshold` | `T.threshold` | changed |
| `c5.exception` | `c5.exception` | `T.exception` | same |
| `c5.modality` | `c5.modality` | `T.modality` | same |
| `c5.threshold` | `c5.threshold` | `T.threshold` | changed |

Every old property maps to exactly one path (12 properties).

## New paths and their origin

| Path (label) | `path_id` | Comes from |
|---|---|---|
| `c1.condition` | `path:6cbf0f5277e...` | `c1.condition` |
| `c1.modality` | `path:4f0c77fc0e8...` | `c1.modality` |
| `c1.threshold` | `path:a79e49f61fa...` | `c1.threshold` |
| `c2.modality` | `path:4abb0dbe9e1...` | `c2.modality` |
| `c2.scope` | `path:783c9a78e42...` | `c2.scope` |
| `c3.modality` | `path:cbcaddbcc62...` | `c3.modality` |
| `c3.threshold` | `path:ebe4df78114...` | `c3.threshold` |
| `c4.ordering` | `path:8c8d2173b4a...` | `c4.order` |
| `c4.threshold` | `path:2ac72c03f6b...` | `c4.threshold` |
| `c5.exception` | `path:b6e92eb4596...` | `c5.exception` |
| `c5.modality` | `path:f6504c99208...` | `c5.modality` |
| `c5.threshold` | `path:844781900b6...` | `c5.threshold` |

Every new path comes from an old property; no path was added as new
(12 paths). C6 holds C1 and C2, so it reuses their paths (the
`path_id` depends on the constraint id, the template id and the version only).
