# CLE Architecture (as built)

This document describes the implementation in `src/cle` as it exists in
this repository — a skeleton (frozen ABI, interfaces, orchestration), not a
categorical-theory implementation. See
[`RFC_ALIGNMENT.md`](RFC_ALIGNMENT.md) for what is deliberately left
unimplemented and why.

## Position in the loop

```
OSS Runtime (complete without CLE)          Optional Pro Layer
──────────────────────────────────          ──────────────────
Observation
      │
semantic-annotator-core
      │
      ▼
Meaning Mapper
      │
      ▼ MeaningMeasurement
Meaning Space Runtime
      │
      ▼ StabilizedTrajectory (optional hand-off)
                                              Categorical Lift Engine
                                                     │
                                                     ▼
                                             Concept / Category / ...
                                                     │
                                                     ▼
                                              HEKBCommitCandidate
                                                     │
                                                     ▼
                                                    HEKB
```

CLE sits strictly downstream of MSR and upstream of HEKB. It imports no
code from either — every crossing is a frozen dataclass value (`cle.abi`)
or a `typing.Protocol` port (`cle.ports`), read by shape.

## Module map

| Module | Responsibility |
|---|---|
| `cle.abi.inputs` | `MeaningStateLike`, `StabilizedTrajectoryLike`, `FieldPriorLike`, `HEKBConceptLike`, `HEKBContextLike` — structural, read-only shapes |
| `cle.abi.outputs` | `Concept`, `ConceptDelta`, `Category`, `CategoryRelation`, `KnowledgeDelta`, `KnowledgeDeltaKind`, `HEKBCommitCandidate` — frozen, owned |
| `cle.errors` | `CLEError` and its three subclasses (`NotStabilized`, `DimensionMismatch`, `NoStrategyConfigured`) |
| `cle.ports.commit` | `CommitSink` — the one outbound port, toward HEKB |
| `cle.categorical_lift.engine` | `CategoricalLiftEngine` — the orchestrator; CLE's only entry point |
| `cle.concept` | `ConceptDiscoveryStrategy` — trajectory -> `Concept`/`ConceptDelta` |
| `cle.category` | `CategoryConstructor` — artifact -> `Category`, optionally |
| `cle.homotopy` | `HomotopyAnalyzer` — are two concepts the same knowledge, differently reached |
| `cle.quotient` | `QuotientConstructor` — collapse an equivalence class into one `Category` |
| `cle.functor` | `FunctorConstructor` — a structure-preserving `Category` -> `Category` mapping |
| `cle.natural_transformation` | `NaturalTransformationAnalyzer` — a mapping between two functors |
| `cle.crystallization` | `KnowledgeCrystallizer` — finalize an artifact into committable form |
| `cle.knowledge_delta` | `KnowledgeDeltaGenerator` — artifact -> `KnowledgeDelta` |
| `cle.commit_candidate` | `CommitCandidateBuilder` — `KnowledgeDelta` -> `HEKBCommitCandidate` |

## The lift, in detail

`CategoricalLiftEngine.lift(trajectory, *, hekb_context=None)`:

1. **Validate.** `trajectory.dwell_steps > 0` and `trajectory.states` is
   non-empty, or `NotStabilized` is raised. CLE never proceeds on a
   trajectory MSR has not actually latched.
2. **Require.** `concept_discovery`, `knowledge_delta_generator`, and
   `commit_candidate_builder` must be configured, or `NoStrategyConfigured`
   names the missing one. These three are the minimum needed to reach a
   `HEKBCommitCandidate` at all.
3. **Discover.** `concept_discovery.discover(trajectory, hekb_context=...)`
   -> one `Concept` or `ConceptDelta`.
4. **Construct, optionally.** If a `category_constructor` is configured, it
   may additionally produce a `Category` from that artifact. If it
   declines (`None`), the lift proceeds with the one artifact from step 3.
5. **Crystallize, optionally.** If a `crystallizer` is configured, every
   artifact from steps 3–4 passes through it before continuing; if not,
   artifacts pass through unchanged (identity — not a fabricated
   normalization).
6. **Generate deltas.** Each artifact becomes one `KnowledgeDelta` via
   `knowledge_delta_generator.generate`.
7. **Build candidates.** Each `KnowledgeDelta` becomes one
   `HEKBCommitCandidate` via `commit_candidate_builder.build`.
8. **Submit, optionally.** If a `commit_sink` is configured, every
   candidate is also submitted to it. `lift()` always returns the tuple of
   candidates regardless.

A lift over a trajectory with no category formed returns one candidate; a
lift where `category_constructor` forms a `Category` returns two — one for
the concept-level artifact, one for the category.

## What CLE deliberately does not do

- **Measure** — that is Meaning Mapper's arrow, upstream of MSR, two hops
  before CLE ever sees anything.
- **Evolve runtime meaning-space state** — that is MSR's; CLE reads only
  what MSR already decided was stabilized.
- **Decide categorical-theory algorithms** — every stage in the module map
  above is an interface. This repository composes them; it does not
  implement homotopy equivalence, quotient collapse, functor construction,
  or natural-transformation analysis. See `RFC_ALIGNMENT.md`.
- **Write to HEKB** — `HEKBCommitCandidate` is a proposal. Acceptance is
  HEKB's decision alone.
- **Import neighbour code** — every neighbour is a structural `Protocol`
  or a frozen ABI value, never a shared class.
