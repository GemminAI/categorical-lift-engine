# CLE Architecture (as built)

This document describes the implementation in `src/cle` as it exists in
this repository. It started as a pure skeleton (frozen ABI, interfaces,
orchestration) and is now, per RFC-CLE001–005, in an experimental
implementation phase: concrete categorical-theory algorithms are being
added phase by phase (see the Implementation Order in the mission brief),
each validated by tests before the next phase starts. See
[`RFC_ALIGNMENT.md`](RFC_ALIGNMENT.md) for exactly what is implemented,
what remains interface-only, and every ABI addition made along the way.

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
| `cle.abi.outputs` | `Concept`, `ConceptDelta`, `Category`, `CategoryRelation`, `ConceptMorphism`, `MorphismType`, `KnowledgeDelta`, `KnowledgeDeltaKind`, `HEKBCommitCandidate` — frozen, owned (`ConceptMorphism`/`MorphismType` added Phase 1, see `RFC_ALIGNMENT.md`) |
| `cle.errors` | `CLEError` and its five subclasses (`NotStabilized`, `DimensionMismatch`, `NoStrategyConfigured`, `FunctorialityViolation`, `InvalidTrajectory` — latter two added Phase 1) |
| `cle.identity` | `deterministic_id` — content-addressed id generation, added Phase 1 |
| `cle.geometry` | `euclidean_distance` — shared geometric primitive, added Phase 2 |
| `cle.ports.commit` | `CommitSink` — the one outbound port, toward HEKB |
| `cle.categorical_lift.engine` | `CategoricalLiftEngine` — the orchestrator; CLE's only entry point |
| `cle.concept` | `ConceptDiscoveryStrategy` (interface) + `FunctorialConceptLift` (Phase 1: object lifting) — trajectory -> `Concept`/`ConceptDelta` |
| `cle.morphism` | `MorphismLiftStrategy` (interface, added Phase 1) + `IdentityInclusionMorphismLift` (Phase 1: morphism lifting) — a lifted concept -> its `ConceptMorphism`s |
| `cle.category` | `CategoryConstructor` — artifact -> `Category`, optionally |
| `cle.homotopy` | `HomotopyAnalyzer` — are two concepts the same knowledge, differently reached; `HomotopyPathAnalyzer` (interface, added Phase 2) + `EpsilonGraphBettiAnalyzer` (Phase 2: single-scale graph Betti numbers) — trajectory-level topology |
| `cle.quotient` | `QuotientConstructor` — collapse an equivalence class into one `Category` |
| `cle.functor` | `FunctorConstructor` (interface) + `CanonicalInclusionFunctorConstructor` (Phase 1: functor construction) — a structure-preserving `Category` -> `Category` mapping |
| `cle.natural_transformation` | `NaturalTransformationAnalyzer` — a mapping between two functors |
| `cle.crystallization` | `KnowledgeCrystallizer` — finalize an artifact into committable form |
| `cle.knowledge_delta` | `KnowledgeDeltaGenerator` — artifact -> `KnowledgeDelta` |
| `cle.commit_candidate` | `CommitCandidateBuilder` — `KnowledgeDelta` -> `HEKBCommitCandidate` |
| `cle.evolution` *(experimental, Phase 4)* | `CategoryEvolutionTracker` (interface: `detect_evolution`, `apply_events`, `trace_lineage`) + `GeometricEvolutionTracker` — `NodeState` pairs -> `EvolutionEvent`s (all five: BIRTH/DEATH/DRIFT exact, MERGE/SPLIT a disclosed proximity heuristic), `LineageSnapshot` replay, and ancestry-graph traversal. Deliberately outside `cle.abi` and not wired into `CategoricalLiftEngine.lift()` — see `RFC_ALIGNMENT.md`'s Phase 4 section for why, and what "experimental" means concretely here. |

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
- **Decide categorical-theory algorithms it hasn't implemented yet** — as of
  Phase 2, object lifting, morphism lifting, functor construction
  (`FunctorialConceptLift`, `IdentityInclusionMorphismLift`,
  `CanonicalInclusionFunctorConstructor`), and single-scale trajectory
  topology (`EpsilonGraphBettiAnalyzer`) have concrete implementations;
  quotient collapse and natural-transformation analysis remain
  interface-only, pending later phases. `EpsilonGraphBettiAnalyzer` is
  itself deliberately scope-limited — no persistent homology, no
  simplicial-complex library — see `RFC_ALIGNMENT.md` for exactly what its
  Betti numbers do and don't prove.
- **Write to HEKB** — `HEKBCommitCandidate` is a proposal. Acceptance is
  HEKB's decision alone.
- **Import neighbour code** — every neighbour is a structural `Protocol`
  or a frozen ABI value, never a shared class.
