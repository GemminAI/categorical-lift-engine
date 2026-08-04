# Boundaries

Boundary before algorithm. If a responsibility below is not listed under
**Owns**, Categorical Lift Engine does not implement it — it is delegated
to whichever neighbor owns it, or it does not exist in this repository at
all.

## Categorical Lift Engine (CLE)

**Input:** `StabilizedTrajectory`, `MeaningState` history, Runtime Field
Prior (optional), HEKB context (optional) — public ABI shapes only.
**Output:** `Concept`, `ConceptDelta`, `Category`, `CategoryRelation`,
`KnowledgeDelta`, `HEKBCommitCandidate`.

**Owns**

- Categorical Lift (the categorical-theory construction: functor, natural
  transformation, pullback, pushout, commutative diagram)
- Stable trajectory interpretation
- Concept discovery
- Category construction
- Semantic abstraction
- Knowledge crystallization
- Concept evolution
- Homotopy analysis
- Quotient construction
- Functor construction
- Natural transformation analysis
- Knowledge delta generation

**Must not**

- Parse observations
- Normalize observations
- Compute a Metric Tensor
- Estimate Covariance
- Manage Runtime State
- Perform Control
- Execute Reflexes
- Generate Goals
- Perform Planning
- Render Language

CLE accepts only **stabilized** runtime artifacts. It never accepts a raw
observation and never performs semantic measurement — both are Meaning
Mapper's job, upstream of Meaning Space Runtime, two hops before anything
reaches CLE. CLE never writes directly into HEKB: every output is a
*candidate*, proposed through `cle.ports.CommitSink`, never applied
in-process. See [`../README.md#position-in-the-sensos-ecosystem`](../README.md#position-in-the-sensos-ecosystem)
for why this is an optional extension, not a required stage.

## Ecosystem responsibility table

| Component | Input | Output | Owns | Must not |
|---|---|---|---|---|
| `semantic-annotator-core` | MeasuredObservation | HEXT Observation | Normalization, schema, ABI | Meaning measurement, memory, runtime, control |
| Meaning Mapper | HEXT Observation | MeaningMeasurement | Geometric measurement, Semantic Projection | Runtime, memory, control, language, concept/category generation |
| MSR (`meaning-space-runtime`) | MeaningMeasurement | Runtime Meaning State; `StabilizedTrajectory` to CLE | Meaning-space state, time evolution, potential field, drift | Observation parsing, measurement, memory |
| **Categorical Lift Engine (CLE)** | `StabilizedTrajectory` / `MeaningState` history | `Concept`, `ConceptDelta`, `Category`, `CategoryRelation`, `KnowledgeDelta`, `HEKBCommitCandidate` | Categorical Lift, trajectory interpretation, concept discovery, knowledge crystallization | Measurement, runtime state evolution, control |
| HEKB | `HEKBCommitCandidate` (accept/reject) | — | Long-term memory, concepts, semantic structure, commit decisions | Runtime, measurement, control |
| NVS-Kernel | `KernelView` (from MSR) | Control decisions | Control, reflex, feedback, trajectory | Observation, measurement, language |
| LLM | — | Natural language rendering | Natural language rendering, code rendering, prior knowledge | Source of truth, runtime authority, measurement authority |

## Crossings are structural, not shared imports

CLE does not import `semantic-annotator-core`, `meaning_mapper`, or `msr`.
`cle.abi.inputs.StabilizedTrajectoryLike` is a `typing.Protocol` describing
the subset of `msr.abi.StabilizedTrajectory`'s shape CLE reads — any object
of that shape, from any producer, satisfies it. This mirrors
`meaning-mapper`'s own convention (`docs/BOUNDARIES.md`, "Crossings are
structural, not shared imports") and `RFC-MSR01` Section 4: "any object
satisfying a port's shape MAY be bound."

The same discipline applies in the output direction: `cle.ports.CommitSink`
is the only crossing toward HEKB, and it is a `Protocol`, not an import of
HEKB code.

## Boundary validation checklist

Every public API in this repository is checked against this table before
being added:

| Direction | Allowed types | Disallowed |
|---|---|---|
| Input | `StabilizedTrajectoryLike`, `MeaningStateLike`, `FieldPriorLike`, `HEKBContextLike`/`HEKBConceptLike` (all `cle.abi.inputs`, structural) | `MeaningMeasurement`, raw observations, any `msr`/`meaning_mapper`/`semantic_annotator_core` internal type |
| Output | `Concept`, `ConceptDelta`, `Category`, `CategoryRelation`, `KnowledgeDelta`, `HEKBCommitCandidate` (all `cle.abi.outputs`, frozen) | Direct HEKB writes, control decisions, rendered language |

An API that would require reaching inside MM or MSR's internals to
implement is redesigned before it is added, not shipped with an internal
import.
