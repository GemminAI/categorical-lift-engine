# CLE × NVS-Kernel Recovery Integration — Artifacts

Verification artifacts for connecting CLE's `create_app(recovery_engine=...)`
composition root to NVS-Kernel's real `ThreeViewTrajectoryRecovery`. This is
integration verification, not calibration — no semantic claims are made
about the output; see [`integration_report.md`](integration_report.md) §13
and the top-level [`docs/CLE_NVS_RECOVERY_INTEGRATION_REPORT.md`](../../docs/CLE_NVS_RECOVERY_INTEGRATION_REPORT.md).

## Layout

- `audit/compatibility.json` — the CLE-contract-vs-NVS-implementation matrix.
- `nvs_unit/` — NVS-Kernel's `ThreeViewTrajectoryRecovery` exercised alone,
  read-only, against the real (unmodified) `nvs-kernel` repo:
  - `request.json` — the synthetic controlled input used (dimension 3,
    orthogonal unit vectors for Subject/Observer/Human).
  - `run_01.json`/`run_02.json`/`run_03.json` — three repeated runs with
    proper `numpy.ndarray` inputs; identical `canonical_sha256` across all
    three confirms determinism.
  - `tuple_input_probe.json` — the same call shape `CLEEngine.recover`
    actually uses (plain `tuple[float, ...]`), reproducing the
    `AttributeError` the adapter fixes, with a full traceback.
- `cle_http/` — the real end-to-end path: `nvs_kernel`'s
  `ThreeViewTrajectoryRecovery` wrapped in CLE's `NumpyCoercingRecovery`,
  served via `create_app`, hit over real HTTP.
  - `request.json`, `response.json` — one representative `/recover` call.
  - `metrics.json` — status code, determinism across 3 calls, latency, and
    the `/health`/`/lift`/`/pullback`/`/compress` regression check results.

## Input source

All inputs here are **synthetic controlled input** (§13/§14 of the task
prompt) — three orthogonal unit vectors, not GPT-OSS output and not a
value MSR/NVS-Kernel produced live. Dimension (3) and coordinates were
chosen for this test, not read from any schema that mandates a specific
dimension (neither CLE's `ConceptInput.states[i].theta: list[float]` nor
NVS-Kernel's `EuclideanManifold(dimension)` fixes one). Using
NVS-Kernel-generated state was left as a follow-up — see the top-level
report's "Unresolved Issues"/"Recommended Next Step".
