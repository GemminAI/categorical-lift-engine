# CLE × NVS-Kernel Recovery Integration Audit

Pre-implementation, read-only audit of both repositories, preceding the
`NumpyCoercingRecovery` adapter added by this phase. Full artifacts and
results: [`../experiments/cle_nvs_recovery_integration/`](../experiments/cle_nvs_recovery_integration/).
See [`CLE_NVS_RECOVERY_INTEGRATION_REPORT.md`](CLE_NVS_RECOVERY_INTEGRATION_REPORT.md)
for the post-implementation result and gate decision.

## Repository versions

| | CLE | NVS-Kernel |
|---|---|---|
| Path | `/Users/tomonam3/GemminAI/categorical-lift-engine` | `/Users/tomonam3/GemminAI/nvs-kernel` |
| Remote | `git@github.com:GemminAI/categorical-lift-engine.git` | `git@github.com:GemminAI/nvs-kernel.git` |
| Branch | `main` | `main` |
| HEAD | `74d8387 Merge claude/cle-fastapi-service-phase1 into main` | `ad99c97 Merge feat/rfc-sensos16-v3-phase1 into main` |
| Version | 0.1.0 | 5.0.0 |
| Working tree | uncommitted repair from the prior "CLE Functional Repair" phase (`src/cle/api/app.py`, `src/cle/api/router.py`, new `docs/`/`tests/` files); this phase's changes land on top | clean |

## Symbol locations

**CLE**: `ThreeViewRecoveryLike` — `src/cle/ports/recovery.py:15`. `recovery_engine` —
`CLEEngine.__init__` (`src/cle/runtime/engine.py:224`), `create_app`
(`src/cle/api/app.py:57`, added in the prior repair phase). `get_engine` —
`src/cle/api/router.py:42`. `/recover` route — `src/cle/api/router.py:120`.
`recover_state` call site — `src/cle/runtime/engine.py:391-396`.

**NVS-Kernel**: `ThreeViewTrajectoryRecovery` —
`nvs_kernel/nvs_kernel_physics/recovery.py:41`. `recover_state` — same
file, line 90. Not wired into NVS-Kernel's own runtime container, API
router, or `control/tiers.py` (a comment there mentions "recovery" only in
prose, not as a wired dependency) — it is a standalone physics primitive,
exercised only by `tests/test_nvs_kernel_recovery.py`.

## Construction requirements (§5/§8 of the task)

`ThreeViewTrajectoryRecovery(manifold: Manifold, *, weights=(0.33,0.33,0.34))`
requires a `nvs_kernel.manifold.base.Manifold`. The simplest concrete one,
`EuclideanManifold(dimension: int)`
(`nvs_kernel/manifold/euclidean.py:21`), needs only a dimension — no YAML,
no environment variables, no filesystem access at the call site itself.

However, **importing** `nvs_kernel.manifold.euclidean` transitively imports
`nvs_kernel/manifold/__init__.py`, which imports `nvs_kernel.config.settings`
(for `GeometrySettings`), which requires `pyyaml` and `pydantic-settings` —
both present in NVS-Kernel's own `.venv` (its own declared dependencies),
neither present in CLE's `.venv` (correctly — CLE has no NVS-Kernel
dependency and none was added). This is a real fact about whatever process
composes the two, not a CLE or NVS-Kernel defect.

## The confirmed incompatibility

`cle.runtime.engine._coordinates_of` produces plain `tuple[float, ...]`
vectors; `CLEEngine.recover` passes these directly to
`recovery_engine.recover_state(...)` and `.compute_recovery_gradient(...)`
with no conversion. Every `nvs_kernel.manifold.Manifold` method
(`distance`, `log_map`, `project_point`) calls `require_same_dimension`,
which reads `.shape` off both arguments (`nvs_kernel/linalg.py:38-40`).

Reproduced directly against the real, unmodified NVS-Kernel package
(`experiments/cle_nvs_recovery_integration/nvs_unit/tuple_input_probe.json`):

```
AttributeError: 'tuple' object has no attribute 'shape'
  File ".../nvs_kernel_physics/recovery.py", line 106, in recover_state
    gradient = self.compute_recovery_gradient(position, x_subject, x_observer, x_human)
  File ".../nvs_kernel_physics/recovery.py", line 84, in compute_recovery_gradient
    w.subject * log(current_x, x_subject)
  File ".../manifold/euclidean.py", line 46, in log_map
    require_same_dimension(base, target)
  File ".../linalg.py", line 39, in require_same_dimension
    if left.shape != right.shape:
AttributeError: 'tuple' object has no attribute 'shape'
```

This is exactly the class of failure §22 of the task warns against treating
as "compatible because the method names match": the signatures are
identical, the semantics line up, and it still crashes on first contact.

Full compatibility matrix: `experiments/cle_nvs_recovery_integration/audit/compatibility.json`.

## Resolution: minimal adapter, CLE-side, no NVS-Kernel import

`cle.ports.recovery.NumpyCoercingRecovery` (new) wraps any
`ThreeViewRecoveryLike` and coerces every vector argument to
`numpy.ndarray(dtype=float64)` before delegating. It:

- Imports only `numpy` (already a CLE dependency) — no `nvs_kernel` import
  anywhere in `cle`.
- Is generic, not NVS-Kernel-specific — it fixes CLE's own output shape
  against the Protocol's declared-but-unenforced `Any` typing, useful for
  any numpy-array-expecting implementation, not just this one.
- Does not modify `ThreeViewRecoveryLike`'s signature or `CLEEngine`.

Composition (owned entirely by the process pairing the two, outside both
repositories):

```python
from nvs_kernel.manifold.euclidean import EuclideanManifold
from nvs_kernel.nvs_kernel_physics.recovery import ThreeViewTrajectoryRecovery
from cle.api.app import create_app
from cle.ports.recovery import NumpyCoercingRecovery

real = ThreeViewTrajectoryRecovery(EuclideanManifold(dimension))
app = create_app(recovery_engine=NumpyCoercingRecovery(real))
```

## Non-goals / boundaries respected

No NVS-Kernel source file was changed (`git status` in `nvs-kernel/` stayed
clean throughout). No `nvs_kernel` import was added to `cle`. No GPT-OSS
was used or referenced. EXP-CLE-0001+ and TCK were not run. No commit or
push was made in either repository.
