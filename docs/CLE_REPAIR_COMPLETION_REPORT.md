# CLE Functional Repair Completion Report

Scope: repair `/recover`'s functional gap so CLE reaches a "calibratable"
implementation state. NVS-Kernel, GPT-OSS, TCK, and EXP-CLE-000x were not
touched. No commit was made. Full audit preceding this repair:
[`CLE_REPAIR_AUDIT.md`](CLE_REPAIR_AUDIT.md).

## 1. Initial Failure

`POST /recover` returned `HTTP 503 {"detail": "recovery_engine is not
configured"}` on every request against the module-level `cle.api.app:app` —
confirmed live and reproduced locally (§5).

## 2. Root Cause

Not a defect in `CLEEngine`, the `ThreeViewRecoveryLike` Protocol, or the
router — all three already worked correctly and were already 100%
test-covered (`tests/test_runtime_engine.py`, `tests/test_api_recover.py`).
The 503 is `NoStrategyConfigured`, the same deliberate "fail loudly, not
fabricate" convention used elsewhere in this codebase
(`NotStabilized`, `FunctorialityViolation`).

The actual gap: this repository shipped **no supported way to compose a
configured `CLEEngine` into a servable app**. `src/cle/api/app.py` built one
fixed, unconfigured `app` at import time; the only override mechanism
(`app.dependency_overrides[get_engine]`) is a FastAPI test-time pattern that
no real entrypoint (`uvicorn cle.api.app:app`) could reach. Every
deployment that imports the bare `app` gets the permanently-unconfigured
default forever, regardless of what recovery implementation exists at
deploy time — exactly the behavior observed live.

## 3. Repair

Added `create_app(*, recovery_engine=None, hekb_store=None) -> FastAPI` to
`src/cle/api/app.py` — an explicit, testable composition-root entrypoint.
It builds a fresh `FastAPI` instance (same router, same exception handlers,
factored into a shared `_build_app()` helper to avoid duplicating the three
handler registrations) wired to a `CLEEngine(recovery_engine=...,
hekb_store=...)` via `dependency_overrides[get_engine]` — formalizing what
tests already did manually into a first-class production path.

**Changed files:**
- `src/cle/api/app.py` — added `create_app`, extracted `_build_app()`;
  module-level `app` unchanged in behavior (still unconfigured by default).
- `src/cle/api/router.py` — `get_engine` docstring updated to point at
  `create_app` as the production composition path.
- `tests/test_api_create_app.py` — new, five tests (Priority 3/§14 A–F).
- `docs/CLE_REPAIR_AUDIT.md` — new, pre-implementation audit.

**Not changed:** `cle.runtime.engine`, `cle.ports.recovery`, `cle.api.models`,
`cle.api.router`'s request handlers, any `cle.topology`/`cle.compression`
module, `eps` default, `/lift`/`/pullback`/`/compress` behavior. No import
of `nvs_kernel` was added anywhere in `cle` — `create_app` accepts a
`ThreeViewRecoveryLike`-shaped object; building a real one (with its
`Manifold`) remains entirely the caller's responsibility, per
`docs/BOUNDARIES.md`'s "CLE imports no HEKB or NVS-Kernel code."

## 4. Tests

**Before repair:** 275 passed, 100% coverage (already green — the bug was
never a test failure, since the 503 was the tested, intended behavior of
the default app).

**Added** (`tests/test_api_create_app.py`, mapped to the audit's §14 test plan):
- Test F — `create_app()` with no arguments still 503 (default production
  startup must not silently succeed).
- Test B/E — `create_app(recovery_engine=fake)` → 200, `converged`,
  `recovered_state_id`, `reconstructed_closure.recovered_state` all present
  and well-typed.
- Test C — malformed `/recover` request → 422.
- Test D — same input 3×, byte-identical response — determinism preserved.
- Isolation check — `create_app`'s configured instance and the default
  `app` are independent; configuring one never leaks into the other.

**After repair:** 280 passed, 100% coverage (`pytest -q --cov=cle
--cov-report=term-missing`, `fail_under = 100`). `ruff check src tests`:
all checks passed. `mypy` (strict): no issues in 72 source files.

## 5. API Verification

Two live local `uvicorn` processes, real HTTP (not `TestClient`):

**Default app (`uvicorn cle.api.app:app`) — unchanged, BEFORE-state:**
- `GET /health` → 200 `{"status":"ok","service":"cle","version":"0.1.0"}`
- `POST /recover` → **503** `{"detail":"recovery_engine is not configured"}`
  (identical to the originally reported failure — confirms the default
  entrypoint's behavior was deliberately preserved, not just re-tested)

**Composed app (`create_app(recovery_engine=<fake ThreeViewRecoveryLike>)`), AFTER-state:**
- `GET /health` → 200
- `POST /lift` (4-point square) → 200, `betti (1,0,1)`, `euler_characteristic 2` — matches the pre-existing, unmodified `/lift` behavior
- `POST /pullback` → 200
- `POST /recover` → **200** `{"recovered_state_id":"recovered:...","reconstructed_closure":{...,"recovered_state":[0.333...,0.333...]},"three_view_discrepancy":0.0,"converged":true}`
- `POST /compress` → 200

BEFORE/AFTER for `/recover` confirmed directly, side by side, over real
sockets, using the two separate app instances above.

## 6. Determinism

`/recover`'s existing implementation was already free of random seeds or
timestamps (confirmed by reading `CLEEngine.recover`, unchanged by this
repair). Added `test_create_app_recover_is_deterministic_across_repeated_calls`
asserts three identical calls return byte-identical JSON. `recovered_state_id`
is content-addressed (`cle.identity.deterministic_id`), not random.

## 7. Compatibility

`/lift`, `/pullback`, `/compress` request/response shapes and existing test
expectations are untouched — same test files, same assertions, all still
passing. The default `cle.api.app:app` singleton's behavior (including its
503-by-default) is unchanged; `create_app()` called with no arguments is
verified equivalent to it. No breaking change to any existing public name;
`create_app` is a pure addition to `__all__`.

## 8. Remaining Limitations

- **The live GCP deployment is not automatically fixed by this repair.**
  Whatever process starts that deployment still needs to call
  `create_app(recovery_engine=<real NVS-Kernel-backed instance>)` instead of
  importing the bare `app` — that composition script lives outside this
  repository and was out of scope (no NVS-Kernel changes, no production
  deploy without separate approval, per instructions).
- **No Dockerfile exists in this repository** (confirmed during the audit —
  none present before or after this repair). Docker verification (§22 of
  the task) was therefore not applicable; verification used two local
  `uvicorn` processes instead (§5). Adding deployment infrastructure was
  treated as out of scope for a functional repair.
- Building a real `ThreeViewTrajectoryRecovery` requires an
  `nvs_kernel.manifold.base.Manifold`, which needs NVS-Kernel's own
  geometry configuration — CLE has no way to construct this correctly
  itself without reaching into NVS-Kernel internals, which was explicitly
  disallowed. `create_app` provides the seam; the concrete instance is a
  deployment-side follow-up.
- `eps=1.5` (default `/lift` Vietoris–Rips threshold) was flagged as a risk
  in the audit and left untouched, per instructions.

## 9. Not Yet Validated

EXP-CLE-0001 through EXP-CLE-0006 (calibration), TCK conformance,
GPT-OSS integration. None of these were run or implied by this repair.

## 10. Recommended Next Step

Before running EXP-CLE-0001: update whatever process starts the live
deployment to call `cle.api.app.create_app(recovery_engine=...)` with a
properly constructed NVS-Kernel `ThreeViewTrajectoryRecovery` (built with
its own `Manifold`, per that repo's own settings/config conventions),
instead of importing `cle.api.app:app` directly, then re-probe `/recover`
against the live endpoint to confirm 200 there too — that step is
deployment-side and needs its own separate approval (per instructions,
§22/§26), not a CLE source change.
