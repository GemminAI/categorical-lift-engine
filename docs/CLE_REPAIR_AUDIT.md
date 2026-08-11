# CLE Functional Repair Audit — `/recover` 503

Status: **audit only, no source changes**. Written before any repair code.
Scope: `POST /recover` returning `HTTP 503 recovery_engine is not configured`
in the live deployment. NVS-Kernel, GPT-OSS, and TCK are out of scope and
untouched by this document and by the repair that follows it.

## 1. Current runtime architecture

`categorical-lift-engine` is a Python package (`src/cle`, import name `cle`),
FastAPI service, `uv`/`hatchling` build, 0.1.0. Two architectural layers
coexist in this repo:

- **The v1/v2 skeleton** — `cle.categorical_lift.engine.CategoricalLiftEngine`,
  described by `README.md` and `docs/ARCHITECTURE.md`. This is a
  `StabilizedTrajectory -> HEKBCommitCandidate` pipeline built from injected
  `Protocol` strategies (`ConceptDiscoveryStrategy`, `CommitCandidateBuilder`,
  etc.). It has no HTTP surface and is unrelated to `/recover`.
- **The v3 runtime + API** — `cle.runtime.engine.CLEEngine`
  ([engine.py](../src/cle/runtime/engine.py)), exposed over HTTP by
  `cle.api` ([router.py](../src/cle/api/router.py),
  [app.py](../src/cle/api/app.py)). This is what actually serves `/lift`,
  `/pullback`, `/recover`, `/compress`. **`docs/ARCHITECTURE.md` and
  `README.md` do not describe this layer at all** — they predate it. There is
  no architecture doc for `cle.runtime`/`cle.api`; the only description of it
  lives in module docstrings and `docs/RFC_ALIGNMENT.md`.

`cle.api.app` builds one module-level `FastAPI` instance:

```python
# src/cle/api/app.py:20-21
app = FastAPI(title="Categorical Lift Engine", version=__version__)
app.include_router(router)
```

There is no application factory, no `lifespan` hook, no `app.state`, no
settings/config module anywhere in this repository (confirmed by repo-wide
grep). The documented run command is literally `uvicorn src.cle.api.app:app`
([app.py:3](../src/cle/api/app.py#L3)) — i.e. "import the fixed module-level
`app` object and serve it," with no composition step in between.

No `Dockerfile`, `docker-compose.yml`, or other deployment config exists in
this repository.

## 2. Current `/recover` request path

```
POST /recover
  -> cle.api.router.recover()                    [router.py:118-128]
       engine: CLEEngine = Depends(get_engine)    [router.py:120]
  -> CLEEngine.recover(subject, observer, knowledge)  [engine.py:356-411]
       if self._recovery_engine is None:
           raise NoStrategyConfigured("recovery_engine is not configured")  [engine.py:362-363]
  -> cle.api.app._no_strategy_configured_handler   [app.py:24-28]
       -> JSONResponse(status_code=503, content={"detail": str(exc)})
```

This is the exact path that produced the observed `HTTP 503
recovery_engine is not configured`.

## 3. `CLEEngine` construction

`CLEEngine.__init__` ([engine.py:219-230](../src/cle/runtime/engine.py#L219))
accepts `recovery_engine: ThreeViewRecoveryLike | None = None` and
`hekb_store: Any | None = None`, both optional, both `None` by default.

The router's dependency provider constructs exactly one instance, at import
time, with no arguments:

```python
# src/cle/api/router.py:39
_default_engine = CLEEngine()

def get_engine() -> CLEEngine:
    ...
    return _default_engine
```

Every request to `/lift` and `/recover` in a plain `uvicorn
cle.api.app:app` process is served by this single unconfigured instance.
Nothing in this repository ever constructs a `CLEEngine` with a
`recovery_engine` outside of tests.

## 4. `recovery_engine` injection point

The router's own docstring already names the gap precisely:

```python
# src/cle/api/router.py:42-53
def get_engine() -> CLEEngine:
    """Dependency-injection point for `CLEEngine`.

    The default instance has no `recovery_engine`/`hekb_store` configured —
    both are generic outbound hooks (...) that a real HEKB client satisfies
    structurally; CLE holds no concrete store implementation of its own.
    Owned by whatever composes CLE into a running system, not by this API.
    Override via `app.dependency_overrides[get_engine]` to inject a
    configured instance.
    """
```

The *only* documented override mechanism is
`app.dependency_overrides[get_engine] = ...` — a FastAPI mechanism that
exists and works (see §7), but is conventionally a **test-time** pattern,
not something a production entrypoint (`uvicorn module:app`) can reach, since
`app` is a plain module attribute and nothing calls
`dependency_overrides` outside of `tests/`. There is no application factory,
settings object, or startup hook a real deployment could use to supply a
configured `CLEEngine` before `uvicorn` starts serving traffic.

**This is the exact and only repair point**: the injection *mechanism*
(`Depends(get_engine)`, the `ThreeViewRecoveryLike` Protocol, `CLEEngine`'s
constructor parameter) all already work correctly. What is missing is a
production-usable way to reach that mechanism from outside a test file.

## 5. `ThreeViewRecoveryLike` contract

[`src/cle/ports/recovery.py`](../src/cle/ports/recovery.py) — a
`@runtime_checkable Protocol`:

```python
def recover_state(
    self, current_x, x_subject, x_observer, x_human, *, steps=20, lr=0.05
) -> Any: ...

def compute_recovery_gradient(
    self, current_x, x_subject, x_observer, x_human
) -> Any: ...
```

The module docstring states this is "Structurally identical to
`nvs_kernel.nvs_kernel_physics.recovery.ThreeViewTrajectoryRecovery`" and
explicitly: "CLE has no dependency on `nvs_kernel`... a Protocol shape, not
a shared class." `cle.ports.__init__` repeats this as a repo-wide invariant:
"CLE imports no HEKB or NVS-Kernel code." `docs/BOUNDARIES.md`'s validation
checklist enforces the same thing generically for every port. This is
confirmed as a deliberate, load-bearing design constraint, not an oversight
— any repair must not add an `nvs_kernel` import to `cle`, static or dynamic
(e.g. no `importlib.import_module("nvs_kernel...")` triggered by an env var
inside this package either — that would still be CLE code importing
NVS-Kernel, just lazily).

## 6. NVS-compatible recovery implementation (read-only reference)

For context only — **not to be copied or imported** —
`/Users/tomonam3/GemminAI/nvs-kernel/nvs_kernel/nvs_kernel_physics/recovery.py`
defines `ThreeViewTrajectoryRecovery`:

```python
class ThreeViewTrajectoryRecovery:
    def __init__(self, manifold: Manifold, *, weights: tuple[float, float, float] = (0.33, 0.33, 0.34)) -> None: ...
```

It structurally satisfies `ThreeViewRecoveryLike` exactly as documented.
Important finding: **its constructor requires an `nvs_kernel.manifold.base.Manifold`
instance** — not a zero-argument construction. Building a real one correctly
requires NVS-Kernel's own geometry/manifold configuration (see
`nvs_kernel/config/settings.py`'s `GeometrySettings`). That construction
knowledge belongs entirely to NVS-Kernel / whatever composes NVS-Kernel with
CLE — it cannot be reconstructed correctly from inside CLE without
duplicating NVS-Kernel's config logic, which both the user's instructions
and this repo's own architecture rules forbid. This rules out any "CLE
auto-builds a working NVS recovery engine from an env var" design — the
correct minimal repair provides the *seam*, not a concrete NVS-Kernel
instance.

`nvs_kernel`'s own FastAPI layer (`nvs_kernel/api/deps.py`) uses an
app-factory + `app.state`/`Depends(get_container)` pattern — `container` is
built once by a composition root and read via `Request`, never a
module-level singleton. This confirms the "sibling" convention across the
two codebases and is the pattern the CLE repair should mirror on the CLE
side (an explicit factory), without importing anything from `nvs_kernel`.

## 7. Current tests

`/recover` and `CLEEngine.recover` are **already fully covered**, and coverage
is currently 100% repo-wide (`tests -q --cov=cle`, 275 passed, `fail_under =
100` in `pyproject.toml`):

- [`tests/test_runtime_engine.py:333-352`](../tests/test_runtime_engine.py#L333) —
  `CLEEngine.recover` raises `NoStrategyConfigured` when unconfigured;
  returns a converged, deterministic result with a `_FakeRecoveryEngine`
  test double injected via the constructor; discrepancy is 0 when all three
  views agree.
- [`tests/test_api_recover.py`](../tests/test_api_recover.py) — `/recover`
  is 503 with `"recovery_engine"` in the detail by default
  (`test_recover_without_a_configured_engine_is_a_503`); 200 with a
  recovered context once `app.dependency_overrides[get_engine]` is set to a
  `CLEEngine(recovery_engine=_FakeRecoveryEngine())`
  (`test_recover_with_a_configured_engine_returns_a_recovered_context`).

The `test_api_recover.py` module docstring states outright:

> "the default `get_engine()` dependency has none configured, so `/recover`
> is expected to report a clean 503 until a caller overrides it — exactly as
> `docs/ARCHITECTURE.md`'s 'fail loudly, not fabricate' convention requires."

## 8. Current failure — reclassified

The 503 is not a latent bug in `CLEEngine`, the router, or the
`ThreeViewRecoveryLike` Protocol. It is the intended, tested behavior of
`NoStrategyConfigured` — the same "fail loudly, not fabricate" convention
`cle.errors` documents for every other unconfigured-stage error in this
codebase (`NotStabilized`, `FunctorialityViolation`, and
`NoStrategyConfigured` itself, already used by
`cle.categorical_lift.engine` before the v3 runtime existed). The engine,
Protocol, and HTTP wiring for `/recover` all work correctly today, proven by
existing passing tests.

**The actual functional gap is one level up**: this repository ships no
supported way to compose a configured `CLEEngine` into a servable `app` for
a real deployment. Every environment that runs `uvicorn cle.api.app:app`
verbatim — including, apparently, the live deployment the user measured —
gets the permanently-unconfigured default, forever, regardless of what
recovery engine implementation is available at deploy time. That is the
functional failure: **no production composition root**, not a defect in the
recovery logic itself.

## 9. Minimal repair point

Add one explicit, testable **application factory** to `cle.api.app`,
additive to (not replacing) the existing module-level `app`:

```python
def create_app(
    *, recovery_engine: ThreeViewRecoveryLike | None = None,
    hekb_store: Any | None = None,
) -> FastAPI:
    """Build a fully wired CLE app. The composition root — whatever process
    pairs CLE with a real recovery_engine/hekb_store implementation — calls
    this directly instead of importing the bare `app` singleton."""
```

Internally, `create_app` builds one `CLEEngine(recovery_engine=...,
hekb_store=...)` and overrides `get_engine` for that app instance (the same
mechanism `app.dependency_overrides[get_engine]` already uses in tests,
formalized into a first-class entrypoint instead of a test-only backdoor).

- The existing module-level `app` / `_default_engine` / `get_engine` stay
  exactly as they are — this is purely additive, so `uvicorn
  cle.api.app:app` keeps behaving exactly as today (503 by default), and
  every existing test keeps passing unmodified.
- No import of `nvs_kernel` is added anywhere in `cle`. A real
  `ThreeViewRecoveryLike` implementation (e.g. a properly constructed
  `ThreeViewTrajectoryRecovery` with its `Manifold`) is built by and remains
  the responsibility of whatever external process composes CLE with
  NVS-Kernel — that process calls `create_app(recovery_engine=<that
  instance>)` and serves the returned `app`. This repository does not gain
  that composition script; wiring the *live* deployment to call
  `create_app(...)` instead of the bare `app` is a deployment-side follow-up
  outside this repo, called out explicitly in §11/Non-goals and in the
  completion report's "Recommended Next Step."
- `router.py`'s `get_engine` docstring gets updated to point at
  `create_app` as the supported production path, replacing the current
  "override via `app.dependency_overrides`" phrasing (which remains true
  for tests but was never meant as production guidance).

Files touched: `src/cle/api/app.py` (add `create_app`), `src/cle/api/router.py`
(docstring only), plus new tests exercising `create_app` (§ below). No
changes to `cle.runtime.engine`, `cle.ports.recovery`, `cle.api.models`, or
any topology/compression module — `/lift`, `/pullback`, `/compress` are
untouched.

## 10. Risks

- **`eps=1.5` (default Vietoris–Rips distance threshold,
  [engine.py:222](../src/cle/runtime/engine.py#L222))** — absolute Euclidean
  threshold; interacts with unit-normalized vectors from NVS `/project`.
  Not evaluated or changed by this repair, per instructions. Flagged only.
- **Two unrelated "CLE architectures" in one package** (`categorical_lift`
  vs `runtime`) with only the latter documented nowhere at the architecture
  level — pre-existing documentation debt, not introduced by this repair,
  but worth a follow-up doc pass (out of scope here).
- **This repair does not make the live GCP deployment return 200.** It adds
  the missing composition seam inside this repository; making the actual
  running service use it requires the deployment process (outside this
  repo) to call `create_app(recovery_engine=...)` with a real, correctly
  constructed NVS-Kernel recovery engine instead of importing the bare
  `app`. That change, and building a real `ThreeViewTrajectoryRecovery` with
  its `Manifold`, is explicitly out of scope (no NVS-Kernel changes, no
  production deploy without separate approval).
- **`app.dependency_overrides` remains available** after this repair (it's
  a FastAPI built-in, not something CLE can remove) — low risk, but worth
  noting it's still technically possible to misuse in production instead of
  `create_app`; documentation is the only guard.

## 11. Non-goals (this repair)

EXP-CLE-0001 through 0006, TCK, GPT-OSS integration, NVS-Kernel changes,
`eps` retuning, `/lift` single-point degeneracy, semantic model or embedding
changes, production/GCP deployment, frontend/UI, unrelated performance work.
`/lift`, `/pullback`, `/compress` behavior and their existing test
expectations are left byte-for-byte unchanged.
