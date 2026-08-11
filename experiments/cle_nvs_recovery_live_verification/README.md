# CLE × NVS-Kernel Live Recovery Verification — Evidence

Read-only verification of the GCP live CLE deployment
(`http://34.61.86.172:8000`), checking whether it uses the
`create_app(recovery_engine=...)` composition path verified locally in the
prior integration phase. No source, deployment, or infrastructure change
was made anywhere in this phase. Full narrative:
[`docs/CLE_NVS_RECOVERY_LIVE_VERIFICATION_REPORT.md`](../../docs/CLE_NVS_RECOVERY_LIVE_VERIFICATION_REPORT.md).

## Layout

- `runtime/health.json`, `runtime/openapi.json` — external API-surface
  evidence (Level 1/2).
- `runtime/version.json` — `/health`'s reported version vs. local CLE
  version, plus the (expected) 404s for `/version` and `/metrics`, neither
  of which CLE defines.
- `runtime/deployment_identity.json`, `runtime/process.txt` — the attempt
  to obtain Level 3/4 runtime-composition evidence via `gcloud`, and why it
  stopped where it did (expired, non-interactive credential; no
  reauthentication attempted, per instructions).
- `recover/request.json` — the exact request body (same synthetic
  orthogonal unit vectors used in the local integration phase).
- `recover/run_01/`, `run_02/`, `run_03/` — three live `POST /recover`
  calls, each with `response.json`, `curl_meta.txt` (status/timing), and
  `metrics.json`.

## Headline result

All three live `/recover` calls returned **HTTP 503**,
`{"detail": "recovery_engine is not configured"}` — byte-identical across
all three runs. This is decisive on its own: it is exactly the default
*unconfigured* `CLEEngine` behavior, regardless of what could or could not
be confirmed about the deployment's runtime process identity.
