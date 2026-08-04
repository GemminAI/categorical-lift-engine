# Categorical Lift Engine (CLE)

**SensOS's optional Knowledge Generation extension.**

CLE turns a `StabilizedTrajectory` — a settled segment of meaning-space
history that Meaning Space Runtime has already produced — into reusable
knowledge: a `Concept`, a `ConceptDelta`, a `Category`, a `CategoryRelation`,
described as a `KnowledgeDelta` and proposed to HEKB as a
`HEKBCommitCandidate`. It does not measure, and it does not run inside any
runtime loop. See [`docs/BOUNDARIES.md`](docs/BOUNDARIES.md).

| | |
|---|---|
| **Product** | Categorical Lift Engine |
| **Repository** | [`GemminAI/categorical-lift-engine`](https://github.com/GemminAI/categorical-lift-engine) |
| **Python package** | `categorical-lift-engine` (import as `cle`) |
| **Input** | `StabilizedTrajectory`, `MeaningState` history (from [`meaning-space-runtime`](https://github.com/GemminAI/meaning-space-runtime), by shape only) |
| **Output** | `Concept`, `ConceptDelta`, `Category`, `CategoryRelation`, `KnowledgeDelta`, `HEKBCommitCandidate` |
| **License** | Reserved — see [License](#license) |
| **Version** | 0.1.0 (skeleton) |

## Position in the SensOS Ecosystem

**semantic-annotator-core, Meaning Mapper, and Meaning Space Runtime are a
complete, self-sufficient OSS stack.** Together, under Apache-2.0 and with
no dependency on this repository, they let you observe, measure, track
meaning state, visualize runtime dynamics, and integrate with LLM
rendering. Nothing in that stack imports or requires CLE, at compile time
or at runtime, and nothing in this repository changes that.

```
OSS Runtime (complete without CLE)          Optional Pro Layer (this repo)
──────────────────────────────────          ──────────────────────────────
Observation                                  StabilizedTrajectory
      │                                             │
semantic-annotator-core                             ▼
      │                                       Categorical Lift Engine
      ▼                                             │
Meaning Mapper                                       ▼
      │                                            Concept /
      ▼                                        Category / KnowledgeDelta
Meaning Space Runtime  ──────────────►               │
      │                StabilizedTrajectory          ▼
      ▼                (optional hand-off)     HEKBCommitCandidate
Runtime Meaning State                                │
(NVS-Kernel, visualization,                          ▼
 LLM rendering, ...)                                HEKB
```

CLE is **installed separately, by choice**. It is not a runtime dependency
of the OSS stack, it does not sit inside the fast loop or the slow loop MSR
already runs, and MSR's own dwell/stabilization behavior is identical
whether CLE is present or absent — MSR only ever hands a
`StabilizedTrajectory` to *whatever satisfies its `LiftPort`*, and is
correct with nothing bound there at all.

Installing CLE **extends** the system: it adds the ability to turn
stabilized semantic trajectories that MSR already produces into reusable,
committable knowledge. It does not complete the system, replace a missing
piece, or unlock functionality the OSS stack was otherwise incomplete
without.

## What it does

`CategoricalLiftEngine.lift()` (`cle.categorical_lift.engine`) is the one
entry point, composing nine owned capabilities in a fixed order:

1. **Concept discovery / evolution** (`cle.concept`) — is this trajectory
   new knowledge (`Concept`) or reinforcement of existing knowledge
   (`ConceptDelta`)?
2. **Category construction** (`cle.category`) — optionally, does this
   artifact belong to a categorical grouping?
3. **Homotopy analysis** (`cle.homotopy`) — are two concepts the same
   underlying knowledge reached by different evidence paths?
4. **Quotient construction** (`cle.quotient`) — collapse a homotopy
   equivalence class into one canonical category.
5. **Functor construction** (`cle.functor`) — a structure-preserving
   mapping between two categories.
6. **Natural transformation analysis** (`cle.natural_transformation`) — a
   mapping between two functors.
7. **Knowledge crystallization** (`cle.crystallization`) — finalize an
   artifact into its immutable, committable form.
8. **Knowledge delta generation** (`cle.knowledge_delta`) — describe the
   crystallized artifact as a `KnowledgeDelta`.
9. **Commit-candidate building** (`cle.commit_candidate`) — wrap the delta
   into the `HEKBCommitCandidate` CLE hands to HEKB.

Stages 3–6 (homotopy, quotient, functor, natural transformation) are inputs
a `CategoryConstructor` implementation may use — they are not parameters of
the engine itself. **This repository defines every stage as an
interface only** (a `typing.Protocol`); none of them ships a
categorical-theory algorithm. See
[`docs/RFC_ALIGNMENT.md`](docs/RFC_ALIGNMENT.md) for why, and what a
concrete implementation still needs to supply.

## What it does not do

CLE never parses or normalizes observations, computes a metric tensor,
estimates covariance, manages runtime state, performs control, executes
reflexes, generates goals, performs planning, or renders language. It never
writes directly into HEKB — every output is a *candidate*, submitted
through `cle.ports.CommitSink` if one is configured, never applied
in-process. Full boundary table: [`docs/BOUNDARIES.md`](docs/BOUNDARIES.md).

## Use

```python
from cle import CategoricalLiftEngine

# concept_discovery, knowledge_delta_generator, and commit_candidate_builder
# are the three required stages — supply your own implementations of the
# corresponding cle.concept / cle.knowledge_delta / cle.commit_candidate
# Protocols. category_constructor, crystallizer, and commit_sink are optional.
engine = CategoricalLiftEngine(
    concept_discovery=my_concept_discovery,
    knowledge_delta_generator=my_knowledge_delta_generator,
    commit_candidate_builder=my_commit_candidate_builder,
    commit_sink=my_hekb_client,  # optional; omit to just receive candidates back
)

candidates = engine.lift(stabilized_trajectory)  # -> tuple[HEKBCommitCandidate, ...]
```

`stabilized_trajectory` may be an `msr.abi.StabilizedTrajectory`, or any
other object of the same shape — CLE type-checks it against
`cle.abi.inputs.StabilizedTrajectoryLike`, a structural `Protocol`, and
never imports `msr`.

## Layout

| Module | Role |
|---|---|
| `cle.abi.inputs` | Structural, read-only shapes CLE reads (never imports the source) |
| `cle.abi.outputs` | The six frozen knowledge artifacts CLE produces |
| `cle.errors` | `CLEError` and its subclasses |
| `cle.ports.commit` | `CommitSink` — CLE's one outbound port, toward HEKB |
| `cle.categorical_lift` | `CategoricalLiftEngine` — the orchestrator |
| `cle.concept` | `ConceptDiscoveryStrategy` interface |
| `cle.category` | `CategoryConstructor` interface |
| `cle.homotopy` | `HomotopyAnalyzer` interface |
| `cle.quotient` | `QuotientConstructor` interface |
| `cle.functor` | `FunctorConstructor` interface |
| `cle.natural_transformation` | `NaturalTransformationAnalyzer` interface |
| `cle.crystallization` | `KnowledgeCrystallizer` interface |
| `cle.knowledge_delta` | `KnowledgeDeltaGenerator` interface |
| `cle.commit_candidate` | `CommitCandidateBuilder` interface |

CLE imports no neighbour code — `semantic-annotator-core`, Meaning Mapper,
and Meaning Space Runtime internals are all off limits. Every crossing is a
`Protocol`-typed port or a frozen ABI value, so anything satisfying the
shape MAY be bound, exactly as `RFC-MSR01` Section 4 already establishes for
its own neighbours.

## Verification

```bash
.venv/bin/python -m pytest tests -q --cov=cle --cov-report=term-missing
.venv/bin/python -m ruff check src tests
.venv/bin/python -m mypy
```

## Product position

CLE is where SensOS's commercial layer begins. It does not monetize
observation, measurement, or runtime execution — those stay OSS, forever
usable without this repository. What CLE represents is the transition from
*meaning* to *knowledge*, and from *runtime* to *reusable semantic asset*:
Knowledge Crystallization, Concept Formation, Semantic Asset Generation,
and Organizational Knowledge.

## License

License status is **intentionally reserved**. This repository sits outside
SensOS's current OSS distribution by product strategy, not by technical
limitation — the OSS stack above is complete without it. Commercial
licensing terms will be determined separately. See [LICENSE](LICENSE) and
[NOTICE](NOTICE).
