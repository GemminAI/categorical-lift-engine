# Migration: old properties to Schema Graph paths

`Constraint Schema 仕様 v0.3` section 6, step 5 (frozen by v0.3.1). The same table in a
machine-readable form is `migration_map.json`; both are written by
`tests/ctp001_v2_builder.py` and `tests/test_ctp001_v2_fixtures.py` checks that they are
what the builder writes and that nothing is missing in either direction.

Old fixtures: `tests/golden/ctp001/` (the obligation is a property
`<constraint_id>.<field>`). New fixtures: this directory (the obligation is a Graph
Path, identified by `path_id`; `path_label` is for display only).
`schema_graph_version` is `"1"`.

## Templates and their required components

| Template | Components | Granularity against the old property |
|---|---|---|
| `T.condition` | `condition` | same |
| `T.scope` | `scope` | same |
| `T.modality` | `modality` | same |
| `T.threshold` | `quantity`, `value`, `unit`, `comparator` | changed |
| `T.exception` | `exempt` | same |
| `T.ordering` | `action`, `after`, `after_edge` | changed |

"same": the old property and the new path are the same unit, so the result of R9 on
the old property and on the path must agree (step 6). "changed": the old property is
one unit, the path is a structure of several components (`T.threshold`: quantity,
value, unit, comparator; `T.ordering`: action, after and the direction of the AFTER
edge), so an example may differ (step 6, not done here).

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
