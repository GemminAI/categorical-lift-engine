# CLE Metrics — draft v0.1

**Status: draft v0.1, Tomo の確認前.** This document and `cle/metrics.py`
describe what is implemented today, not a reviewed specification. Numbers,
thresholds, and even which five metrics matter may change on review.

Implementation: `cle/metrics.py`. Calibration tests (answer known in
advance): `tests/test_metrics_calibration.py`. Golden reference values for
a future Rust port: `tests/golden/`.

## 1. Functorial Invariance Score (FIS)

For a candidate mapping between two finite categories (`object_map`,
`morphism_map`), the fraction of the functor axioms it satisfies, checked
pairwise over every identity and every composable pair:

1. **Identity preservation**: `F(id_A) = id_{F(A)}`.
2. **Composition preservation**: `F(g . f) = F(g) . F(f)`.

`FIS = satisfied / total`. A genuine functor (one that would pass
`cle.topology.category_theory.Functor`'s own strict constructor) scores
`1.0`. Implemented as `functorial_invariance_score`, deliberately *not*
built on top of `Functor` itself — `Functor` raises on the first axiom
violation, which makes it impossible to use for measuring a **partial**
score.

Vacuous case: a candidate with nothing to check (no identities, no
composable pairs in the source category) scores `1.0`.

## 2. Homotopy Class Determinism

Run the *same* persistence-diagram computation `N` times (default `N=3`),
each in an independent process with a different `PYTHONHASHSEED`, and
measure the fraction that produced a bit-identical result to the first run.
Target: `1.0`.

`homotopy_class_determinism` itself takes the `N` already-computed,
already-serialized result strings and only measures agreement — it does
not spawn the processes or compute the diagrams. The serialization
convention (floats via `repr`, diagram rows sorted for a stable order) and
the actual multi-process harness live in
`tests/test_metrics_calibration.py`.

## 3. Entropic Reduction Delta

For a quotient map `q: X -> X/~`, the drop in Shannon entropy (bits)
between `X`'s empirical weight distribution and `X/~`'s:

```
Delta = H(X) - H(X/~)
```

`H(X) = -sum_i p_i log2(p_i)` over `X`'s (renormalized) weights; `H(X/~)`
is the same formula over each class's summed weight.

`Delta >= 0` always — this is the grouping property of Shannon entropy
(coarsening a partition cannot increase its entropy), not a runtime check.
`Delta = 0` exactly when `q` is injective on the support of `X`'s weights
(no two positively-weighted elements actually merge).

## 4. CET Lineage Integrity

For a hash-chained sequence of lineage records, the fraction whose:

1. **Hash link** verifies: `record.prev_hash == sha256(canonical(previous.content))`
   (the first record's `prev_hash` must be `None`), **and**
2. **Transformation claim** verifies, if the record makes one: constructing
   a `cle.topology.natural_transformation.NaturalTransformation` from the
   claim's `(source_functor, target_functor, components)` must not raise
   `FunctorialityViolation` — i.e. the claimed naturality square commutes.

`1.0` is required; anything less means at least one record in the chain
was tampered with (content changed without updating the next record's
`prev_hash`, or a transformation claim that doesn't actually commute).

`TransformationClaim` exists specifically because
`NaturalTransformation`'s own constructor already raises on an invalid
square — a `LineageRecord` must still be constructible when its claim is
wrong (that's the case this metric exists to detect), so validation is
deferred to `cet_lineage_integrity` itself.

## 5. HEKB Transaction Yield

Of the candidates CLE submitted to a HEKB commit sink, the fraction that
were committed (vs. rejected):

```
Yield = committed / submitted
```

Measured in CLE's own tests against `InMemoryHEKBSink`, an in-memory
stand-in — wiring this against the real `hekb-vnext` service is explicitly
separate work, not part of this metric's definition. `submit`'s `accept`
flag stands in for whatever decision the real sink would make; this class
does not simulate HEKB's own acceptance logic.
