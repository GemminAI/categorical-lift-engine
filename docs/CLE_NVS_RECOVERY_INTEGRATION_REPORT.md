# CLE × NVS-Kernel Recovery Integration Report

Verifies that the repaired CLE composition root
(`cle.api.app.create_app(recovery_engine=...)`) actually connects to a real
NVS-Kernel `ThreeViewTrajectoryRecovery`, end to end. Not calibration, not
development on either engine — see [`CLE_REPAIR_COMPLETION_REPORT.md`](CLE_REPAIR_COMPLETION_REPORT.md)
for the prior functional-repair phase this builds on. No commit or push was
made in either repository.

## 1. Objective

Determine whether `NVS-Kernel recovery → ThreeViewRecoveryLike → CLE
/recover` actually works, as a precondition for running EXP-CLE-0001, and
render a gate decision.

## 2. Repository Versions

| | CLE | NVS-Kernel |
|---|---|---|
| Path | `categorical-lift-engine` | `nvs-kernel` |
| Branch / HEAD | `main` @ `74d8387` | `main` @ `ad99c97` |
| Version | 0.1.0 | 5.0.0 |
| Repo state after this phase | uncommitted changes only (this + the prior repair phase) | **unchanged, clean** |

## 3. Existing Contracts

`cle.ports.recovery.ThreeViewRecoveryLike` (Protocol) ↔
`nvs_kernel.nvs_kernel_physics.recovery.ThreeViewTrajectoryRecovery`
(concrete class). Full symbol locations and construction requirements:
[`CLE_NVS_RECOVERY_INTEGRATION_AUDIT.md`](CLE_NVS_RECOVERY_INTEGRATION_AUDIT.md).

## 4. Compatibility Audit

Method signatures, `steps`/`lr` defaults, and return-value handling all
matched (`YES`). The vector-argument *type* did not: NVS-Kernel's
`Manifold` implementations require `numpy.ndarray` (read `.shape`); CLE
passes plain `tuple[float, ...]`. Confirmed by direct reproduction against
the real NVS-Kernel package — `AttributeError: 'tuple' object has no
attribute 'shape'`. Classified `ADAPTER REQUIRED`, not `NO`: the fix is a
small, generic, non-NVS-importing coercion, not a protocol redesign. One
row — whether CLE's `x_subject`/`x_observer`/`x_human` are *semantically*
the same anchors as NVS-Kernel's — is classified `UNRESOLVED`: naming and
vocabulary line up strongly (identical parameter names, identical Japanese
term "三視点拘束"), but no single RFC document in either repository formally
cross-references the two. Full matrix:
[`experiments/cle_nvs_recovery_integration/audit/compatibility.json`](../experiments/cle_nvs_recovery_integration/audit/compatibility.json).

## 5. NVS Recovery Unit Test

`EuclideanManifold(3)` → `ThreeViewTrajectoryRecovery(manifold)`, run
directly against the unmodified `nvs-kernel` package, its own `.venv`. Three
runs with correctly-typed `numpy.ndarray` input: byte-identical
`recovered_state`/`gradient`, identical SHA-256 across all three (see
`experiments/.../nvs_unit/run_0{1,2,3}.json`) — deterministic, no RNG. The
same call with CLE's actual tuple-shaped input reproduced the incompatibility
above (`nvs_unit/tuple_input_probe.json`, full traceback included).

## 6. CLE Composition

Added `cle.ports.recovery.NumpyCoercingRecovery` — a `ThreeViewRecoveryLike`
adapter, `numpy`-only, no `nvs_kernel` import anywhere in `cle`. Composition
(owned by the pairing process, outside both repos):

```python
from nvs_kernel.manifold.euclidean import EuclideanManifold
from nvs_kernel.nvs_kernel_physics.recovery import ThreeViewTrajectoryRecovery
from cle.api.app import create_app
from cle.ports.recovery import NumpyCoercingRecovery

app = create_app(
    recovery_engine=NumpyCoercingRecovery(
        ThreeViewTrajectoryRecovery(EuclideanManifold(dimension=3))
    )
)
```

Run with real `uvicorn`, using NVS-Kernel's own `.venv` (a superset
environment: it already carries fastapi/pydantic/httpx/numpy) with CLE's
`src/` added to `PYTHONPATH`. Neither repository's files were changed to
make this work.

## 7. HTTP `/recover` Verification

`POST /recover` with three synthetic orthogonal unit vectors
(Subject/Observer/Human, dimension 3) → **HTTP 200** every time.
`recovered_state = [0.41145635857568136, 0.2898797039851121,
0.29866393743920644]`, matching the standalone NVS unit test's `run_01`
exactly — the adapter changes nothing numerically. Response schema valid
against `RecoverResponse` (`recovered_state_id`, `reconstructed_closure`,
`three_view_discrepancy`, `converged` all present, correctly typed). A
malformed request (missing `observer`/`knowledge`) → HTTP 422, unchanged.
Full request/response/metrics: `experiments/.../cle_http/`.

## 8. Determinism

Three HTTP calls with identical input → byte-identical response bodies
(including `recovered_state_id`, which is content-addressed via
`cle.identity.deterministic_id`). Three direct NVS-Kernel unit-test calls →
identical SHA-256. No seed was fixed to hide non-determinism — none was
observed; the algorithm is plain gradient descent with no random component
in either repository's implementation.

## 9. Regression Tests

Full CLE suite: **286 passed, 100% coverage** (`fail_under = 100`), up from
275/100% before this phase (11 new tests: 6 for `create_app`, 5 for the new
adapter — from this phase and the prior repair phase combined). `ruff
check`: all checks passed. `mypy` (strict): no issues, 73 source files.
`/health`, `/lift`, `/pullback`, `/compress` re-run against the real
NVS-composed app: identical response bodies to the pre-integration
baseline. Default `app` and `create_app()` with no `recovery_engine`:
still HTTP 503, re-confirmed in this exact combined environment.

## 10. Integration Architecture

```
nvs_kernel.manifold.euclidean.EuclideanManifold
        |
nvs_kernel.nvs_kernel_physics.recovery.ThreeViewTrajectoryRecovery
        |  (wrapped by, composition-root side, numpy-only, no NVS import in CLE)
cle.ports.recovery.NumpyCoercingRecovery
        |  (satisfies)
cle.ports.recovery.ThreeViewRecoveryLike
        |  (injected via)
cle.api.app.create_app(recovery_engine=...)
        |
cle.runtime.engine.CLEEngine.recover()
        |
POST /recover  ->  HTTP 200
```

CLE's boundary discipline ("CLE imports no HEKB or NVS-Kernel code",
`docs/BOUNDARIES.md`) holds throughout: `cle` gained one new file-local
adapter class, zero new imports of `nvs_kernel`. NVS-Kernel gained nothing
— its repository is untouched.

## 11. Confirmed Facts

- NVS-Kernel's recovery module instantiates from a `Manifold` alone; no
  YAML/env/filesystem access at the recovery call site.
- Importing `nvs_kernel.manifold` transitively needs `pyyaml` +
  `pydantic-settings` (NVS-Kernel's own declared deps) — a composition-root
  environment fact, not a CLE dependency change.
- The bare-tuple-vs-ndarray mismatch is real and reproducible, not
  speculative — confirmed with a full traceback against the actual package.
- The adapter resolves it without violating any stated architectural
  boundary in either repository.
- The real, adapted, end-to-end path returns HTTP 200 with a
  schema-valid, deterministic response; existing `/lift`/`/pullback`/`/compress`
  behavior is unchanged.

## 12. Unresolved Issues

- **Semantic equivalence** of CLE's and NVS-Kernel's Subject/Observer/Human
  anchors is asserted by shared vocabulary, not proven by a cross-referenced
  spec present in either repo (compatibility matrix row, §4). Matters for
  EXP-CLE-0001+'s *interpretation* of `/recover`'s output, not for this
  phase's numeric-execution verification.
- **`converged: false`** at the default `steps=20, lr=0.05` for
  well-separated orthogonal test anchors — expected gradient-descent
  behavior at this step count/learning rate, not investigated further
  (retuning either default was out of scope).
- **Exception mapping**: NVS-side `ValueError`s (e.g. `lr <= 0`) are not
  translated to a CLE-specific type; they propagate as bare `ValueError`,
  which `cle.api.app`'s existing handler already maps to HTTP 422 — noted
  as adequate, not specifically tested end-to-end this phase.

## 13. Non-Claims

No claim is made that NVS-Kernel or CLE "understood" anything, that
`/recover` performed causal reasoning, or that the recovered state is
semantically correct — only that the protocol executes, is deterministic,
and returns a schema-valid HTTP response. GPT-OSS was not used anywhere in
this verification; all input was synthetic, explicit numeric state.

## 14. Deployment Status

The live GCP deployment was **not** touched or re-probed this phase (out of
scope, per instructions — "GCP deployment変更は今回の明示的scope外"). Per the
prior repair phase's completion report, that deployment was, as of that
audit, still importing the bare `cle.api.app:app` rather than calling
`create_app(...)`. Whether it has been updated since is unknown and was not
re-checked here; doing so, and wiring it to call `create_app` with a real
NVS-Kernel-backed `NumpyCoercingRecovery`, remains an explicit
deployment-side follow-up requiring separate approval.

## 15. Gate Decision

**CONDITIONAL PASS.**

All ten local success criteria (A–J) were met: the real NVS recovery
implementation instantiates; its incompatibility with CLE's bare
`ThreeViewRecoveryLike` contract was identified and resolved by a minimal,
CLE-side, NVS-import-free adapter; `recover_state` executes for real;
output is deterministic; `create_app(recovery_engine=<real NVS engine>)`
starts; `/recover` returns HTTP 200 with a valid, schema-conformant body;
`/lift`/`/pullback`/`/compress` show no regression; NVS-Kernel's repository
is unmodified; GPT-OSS was not used.

This is **CONDITIONAL**, not unconditional PASS, strictly per §24's own
definition: local integration succeeded, but the live GCP deployment has
not been confirmed to use this composition path (§14) — that gap was
explicitly out of scope this phase, not a defect found here.
