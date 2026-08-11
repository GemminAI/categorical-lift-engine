# Boundaries

Boundary before algorithm. If a responsibility below is not listed under
**Owns**, Categorical Lift Engine does not implement it — it is delegated
to whichever neighbor owns it, or it does not exist in this repository at
all.

## 2026-08-12 revision: Semantic Grounding added

Per explicit user directive (CLE-rebuild session, 2026-08-12), CLE now also
owns **Semantic Grounding of a Prompt/Goal** — 5W1H extraction, S/O/K(t)
triangulation, and `GroundedState` construction (`cle.grounding`, `POST
/ground`). This is a deliberate reversal of this document's prior position
(CLE did not do grounding; that was Meaning Mapper's job) — recorded here,
not silently changed, because 4 other repos' own boundary docs (see the
ecosystem table below) were written assuming the prior split.

**This does not touch the `Must not` list below.** "Parse observations" /
"Normalize observations" refer to raw HEXT `Observation` objects from
`semantic-annotator-core` — CLE still never accepts those, still has no
measurement pipeline, and still does not import `semantic-annotator-core`,
`meaning_mapper`, or `msr`. A **Prompt/Goal** (arbitrary text supplied to
`/ground`) is not an `Observation` in that sense — it has no sensor
provenance, no HEXT schema, and reaches CLE through a wholly new input path
(`cle.grounding`), not through `cle.abi.inputs`'s existing MSR-facing
Protocols. `cle.grounding.embedding` bridges the resulting S/O/K(t) text to
the numeric point clouds `CLEEngine.lift`/`.recover` already required —
Grounding calls that existing engine, it does not bypass or duplicate it.

## Categorical Lift Engine (CLE)

**Input:** `StabilizedTrajectory`, `MeaningState` history, Runtime Field
Prior (optional), HEKB context (optional) — public ABI shapes only.
**Also (new, `cle.grounding`):** Prompt (str), Goal (str), 5W1H/S-O-K(t)
overrides.
**Output:** `Concept`, `ConceptDelta`, `Category`, `CategoryRelation`,
`KnowledgeDelta`, `HEKBCommitCandidate`.
**Also (new, `cle.grounding`):** `GroundedState` (5W1H, S/O/K(t),
fingerprints, point clouds).

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
- **Semantic Grounding of a Prompt/Goal** — 5W1H extraction, S/O/K(t)
  triangulation, GroundedState construction (new, 2026-08-12)

**Must not**

- Parse observations *(HEXT `Observation` objects — unchanged; a Prompt is
  not an Observation, see above)*
- Normalize observations *(same scope note)*
- Compute a Metric Tensor
- Estimate Covariance
- Manage Runtime State
- Perform Control
- Execute Reflexes
- Generate Goals
- Perform Planning
- Render Language

CLE accepts **stabilized runtime artifacts** (unchanged) **and, as of
2026-08-12, Prompt/Goal text for Grounding** (new; see above). It never
accepts a raw HEXT `Observation` and still performs no sensor-level
measurement — that remains Meaning Mapper's job, upstream of Meaning Space
Runtime. CLE never writes directly into HEKB: every output is a
*candidate*, proposed through `cle.ports.CommitSink`, never applied
in-process. See [`../README.md#position-in-the-sensos-ecosystem`](../README.md#position-in-the-sensos-ecosystem)
for why the pre-2026-08-12 scope of this repository is an optional
extension, not a required stage — that positioning is unchanged by adding
Grounding, which is a new front door, not a new dependency on the OSS
runtime stack.

## Ecosystem responsibility table

| Component | Input | Output | Owns | Must not |
|---|---|---|---|---|
| `semantic-annotator-core` | MeasuredObservation | HEXT Observation | Normalization, schema, ABI | Meaning measurement, memory, runtime, control |
| Meaning Mapper | HEXT Observation | MeaningMeasurement | Geometric measurement, Semantic Projection | Runtime, memory, control, language, concept/category generation |
| MSR (`meaning-space-runtime`) | MeaningMeasurement | Runtime Meaning State; `StabilizedTrajectory` to CLE | Meaning-space state, time evolution, potential field, drift | Observation parsing, measurement, memory |
| **Categorical Lift Engine (CLE)** | `StabilizedTrajectory` / `MeaningState` history; **also (new) Prompt/Goal text** | `Concept`, `ConceptDelta`, `Category`, `CategoryRelation`, `KnowledgeDelta`, `HEKBCommitCandidate`; **also (new) `GroundedState`** | Categorical Lift, trajectory interpretation, concept discovery, knowledge crystallization, **Semantic Grounding of a Prompt/Goal (new, 2026-08-12)** | Measurement (of HEXT Observations), runtime state evolution, control |
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
