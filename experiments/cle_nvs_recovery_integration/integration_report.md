# Integration Run Report (artifact-level)

Full narrative report: [`docs/CLE_NVS_RECOVERY_INTEGRATION_REPORT.md`](../../docs/CLE_NVS_RECOVERY_INTEGRATION_REPORT.md).
This file records the mechanics of the run these artifacts came from.

## NVS unit test (`nvs_unit/`)

- Environment: `nvs-kernel/.venv` (its own dependencies, unmodified),
  `nvs-kernel` on `PYTHONPATH`.
- `EuclideanManifold(3)` → `ThreeViewTrajectoryRecovery(manifold)` (default
  weights `(0.33, 0.33, 0.34)`).
- `numpy.ndarray` inputs, `steps=20, lr=0.05`: 3 runs, byte-identical
  `recovered_state`/`gradient`, identical SHA-256
  (`23ae15d2...0953ed3`) across all three — deterministic.
- `tuple[float, ...]` inputs (CLE's actual call shape): `AttributeError`,
  captured with full traceback.

## CLE HTTP test (`cle_http/`)

- Environment: `nvs-kernel/.venv` (superset of CLE's own runtime deps:
  fastapi 0.140.0, pydantic 2.13.4, httpx 0.28.1, numpy already present),
  `categorical-lift-engine/src` added to `PYTHONPATH`. Neither repository's
  files were modified to make this environment work.
- `app = create_app(recovery_engine=NumpyCoercingRecovery(ThreeViewTrajectoryRecovery(EuclideanManifold(3))))`,
  served with real `uvicorn` on `127.0.0.1:8733`.
- `POST /recover` × 3 with the synthetic Subject/Observer/Human vectors →
  HTTP 200 each time, byte-identical response bodies.
- `recovered_state` = `[0.41145635857568136, 0.2898797039851121, 0.29866393743920644]`
  — matches `nvs_unit/run_01.json` exactly, cross-validating that the
  adapter changes nothing numerically versus calling NVS-Kernel directly
  with correctly-typed input.
- `converged: false` — `gradient_norm ≈ 0.1995` at the default
  `steps=20, lr=0.05` does not clear `CLEEngine.recover`'s `1e-3`
  threshold for these well-separated orthogonal anchors. Expected
  numerical-methods behavior for this step count/learning rate, not a
  compatibility defect; not retuned (out of scope).
- Regression: `/health`, `/lift`, `/pullback`, `/compress` all HTTP 200 on
  this same composed app, response bodies identical to the pre-integration
  baseline captured in the CLE Functional Repair phase. Malformed
  `/recover` → HTTP 422.
- Default `app` (and `create_app()` with no `recovery_engine`) re-checked
  in this same environment: still HTTP 503
  `{"detail": "recovery_engine is not configured"}` — unaffected.
