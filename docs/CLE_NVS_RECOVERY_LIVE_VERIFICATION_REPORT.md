# CLE × NVS-Kernel Live Recovery Verification

Read-only check of whether the GCP live CLE deployment reflects the local
integration verified in the prior phase
([`CLE_NVS_RECOVERY_INTEGRATION_REPORT.md`](CLE_NVS_RECOVERY_INTEGRATION_REPORT.md)).
No source code, deployment, container, or process was modified, restarted,
or redeployed. No commit or push was made. Full evidence:
[`../experiments/cle_nvs_recovery_live_verification/`](../experiments/cle_nvs_recovery_live_verification/).

## 1. Objective

Determine, without changing anything, whether
`http://34.61.86.172:8000` is currently serving CLE's `/recover` backed by
a configured (ideally NVS-Kernel-backed) `recovery_engine`, or the default
unconfigured engine — and render a gate decision for EXP-CLE-0001.

## 2. Live Deployment Identity

- `GET /health` → 200, `{"status":"ok","service":"cle","version":"0.1.0"}`
  — version matches the local CLE repo exactly (0.1.0).
- Response header `server: uvicorn` on every request — consistent with a
  direct `uvicorn` process, but this alone does not distinguish
  `uvicorn cle.api.app:app` (the default, unconfigured entrypoint) from a
  `create_app(...)`-based composition — both produce an identically
  titled/versioned, identically routed FastAPI app.
- Runtime process identity (command line, container command, deployment
  manifest, environment variables): **UNRESOLVED**. `gcloud compute
  instances list` failed with an expired, non-interactive credential
  (`Reauthentication failed. cannot prompt during non-interactive
  execution.`). Per instructions, no `gcloud auth login` or configuration
  change was attempted to work around this; no SSH session was opened
  either (a materially more invasive read than a metadata API call). See
  `experiments/.../runtime/deployment_identity.json`.

## 3. API Surface

`GET /openapi.json` → 200, 8551 bytes. `title: "Categorical Lift Engine"`,
`version: "0.1.0"`, paths `/health`, `/lift`, `/pullback`, `/recover`,
`/compress` — exactly CLE's current router, no extra or missing routes.
`GET /docs` → 200 (Swagger UI reachable). `/version` and `/metrics` both
404 — expected, CLE defines neither route; each probed exactly once, not
retried.

## 4. `/recover` Live Probe

Same request shape and same synthetic orthogonal unit-vector input used in
the local integration phase (`experiments/.../recover/request.json`):
`x_subject=[1,0,0]`, `x_observer=[0,1,0]`, `x_human=[0,0,1]`, dimension 3.

Three live calls, all identical:

```
HTTP 503
{"detail": "recovery_engine is not configured"}
```

This is `cle.errors.NoStrategyConfigured`'s exact message
(`src/cle/runtime/engine.py:363`), surfaced through the same exception
handler (`src/cle/api/app.py`) verified in the functional-repair phase —
i.e. this is precisely the behavior of `CLEEngine()` constructed with no
`recovery_engine`, whether reached via the module-level default `app` or
`create_app()` called with no arguments.

## 5. Determinism

All three runs: identical HTTP status (503) and byte-identical response
body. Deterministic, as expected — there is nothing engine-specific to
vary when the failure occurs before any recovery computation runs.

## 6. Runtime Composition Evidence

No Level 3+ evidence was obtainable this phase (§2). The live `/recover`
response is itself indirect but strong evidence at the *behavioral* level:
a `create_app(recovery_engine=<anything>)` composition, correctly wired,
would not produce this exact message under any input — `NoStrategyConfigured`
is raised only when `CLEEngine._recovery_engine is None`
(`src/cle/runtime/engine.py:362-363`). The observed 503 is therefore
consistent only with **Case A** (bare `uvicorn cle.api.app:app`, default
`app`) or **Case D** (an older deployment predating the `create_app` repair
— which amounts to the same runtime behavior, since neither has a
configured engine). Cases B/C (a working NVS-backed or other configured
composition) are ruled out by this observation, not merely unconfirmed —
a configured engine cannot produce this specific error message.

## 7. Evidence Levels

| Level | Evidence | Status |
|---|---|---|
| 1 — external HTTP response | `/health`, `/recover` × 3 | Obtained, decisive |
| 2 — API/OpenAPI identity | `/openapi.json`, `/docs` | Obtained, consistent with current CLE router |
| 3 — runtime process identity | `gcloud compute instances list`, headers | UNRESOLVED (auth failure) / weak-only (`server: uvicorn`) |
| 4 — application composition identity | deployment manifest, env vars, entrypoint command | UNRESOLVED |
| 5 — actual NVS-backed recovery execution evidence | N/A | Not reached — §6 rules this out behaviorally regardless |

## 8. Confirmed Facts

- The live deployment is reachable, healthy, and running CLE 0.1.0 with
  the exact current route set.
- Live `/recover` returns HTTP 503 `"recovery_engine is not configured"`,
  deterministically, across three independent calls with the same input
  verified locally to succeed once a `recovery_engine` is composed in.
- This response is possible only from an unconfigured `CLEEngine` — it
  behaviorally rules out any working NVS-backed (or other) composition
  currently being live, independent of whether the process-level evidence
  in §2/§6 could be obtained.

## 9. Unresolved Issues

- Exact runtime process/command line, container definition, and deployment
  manifest — blocked by an expired `gcloud` credential; not pursued
  further per instructions (no reauthentication attempted).
- Whether the live deployment is running the pre-repair `cle.api.app:app`
  import verbatim, or a post-repair `create_app()` call with no arguments
  — both are behaviorally indistinguishable from outside (§6) and were not
  disambiguated at the process level (§2).
- Whether the deployment has been redeployed since the prior repair phase
  at all — version match (0.1.0) is consistent with either "not yet
  redeployed" or "redeployed but still uncomposed," and does not
  distinguish them.

## 10. Non-Claims

No claim is made about *why* the deployment is unconfigured (no
speculation about deploy pipeline, CI, or operator intent). No fix,
redeploy, restart, or configuration change was made or attempted. No claim
is made that the local integration verified previously is somehow invalid
— it remains a separately-confirmed local result
(`CLE_NVS_RECOVERY_INTEGRATION_REPORT.md`), unaffected by this deployment's
current state.

## 11. Gate Decision

**D — NOT DEPLOYED.**

Live `/recover` returns 503 `"recovery_engine is not configured"`,
deterministically, on the same input verified locally to succeed. Per §6,
this rules out a working composed engine being live, regardless of the
unresolved process-level evidence in §2/§7. The local integration result
stands as **LOCAL PASS** (unaffected, separately verified); the live
deployment simply does not yet reflect it.

No repair, redeploy, or restart was performed, per instructions. This is
recorded as a deployment-side follow-up for a separate, explicitly
authorized phase — not undertaken here.

**EXP-CLE-0001 gate: still blocked.** Per the task's own rule, EXP-CLE-0001
does not proceed until LIVE PASS; this phase confirms the deployment is
currently NOT DEPLOYED with respect to the NVS-backed recovery
composition, so that gate remains closed.
