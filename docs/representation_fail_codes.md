# FAIL reason codes of `cle.representation`

Fixed by CLE v0.4 ("FAIL の理由コード: A の名前を、docs の一覧に固定する"). The list is taken from the code
(`tests/test_representation_docs.py` compares it with the strings in `checks.py`); the descriptions are one line each.
UNVERIFIABLE reason codes are those of CLE v0.3 section 3 (plus `MORPHISM_UNRESOLVED`, see
`representation_ambiguities.md` #10). Warnings (not statuses) use `MAP_EXTRA_ENTRY` (R8, v0.4 D-14).

| code | meaning |
|---|---|
| `ASSOCIATIVITY_VIOLATION` | R2: two ways of composing three morphisms land on different recorded morphisms. |
| `BRANCH_DROPPED` | R6: a branch of the previous version is gone, or has lost state or morphism ids (v0.4 D-25). |
| `COMPOSITION_ENDPOINT_MISMATCH` | R1: a composition entry whose first, second and result do not chain (f: A->B, g: B->C, h: A->C). |
| `COMPOSITION_NOT_FUNCTIONAL` | R2: the same (first, second) pair is given two different results. |
| `DUPLICATE_ID` | R1: two states, or two morphisms, share an id. |
| `DUPLICATE_IDENTITY` | R2: a state has more than one identity morphism. |
| `ELEMENT_DROPPED` | R6: a state or morphism of the previous version is missing (location kind tells which). |
| `ELEMENT_REWRITTEN` | R6: a state or morphism keeps its id but its content differs from the previous version (v0.4 D-20). |
| `ENDPOINT_MISMATCH` | R1: an identity morphism whose source and target states differ. |
| `FINITE_CATEGORY_REJECTED` | R1: `finite_category_of` found that the existing `FiniteCategory` constructor rejects the history. |
| `FUNCTOR_COMPOSITION_NOT_PRESERVED` | R8: the image of a composition differs from the composition of the images. |
| `FUNCTOR_ENDPOINT_MISMATCH` | R8: a morphism's image does not run between the images of its endpoints. |
| `FUNCTOR_IMAGE_UNRESOLVED` | R8: an image names a state or morphism the target history does not contain (v0.4 D-22). |
| `IDENTITY_MALFORMED` | R3: an identity morphism does not preserve the whole vocabulary or loses information. |
| `IDENTITY_NOT_PRESERVED` | R8: an identity morphism is mapped to something that is not an identity of the image state. |
| `INPUT_TYPE_INVALID` | any rule: a value has a type other than the annotated one (v0.4 D-12); the location names the record. |
| `INVERSE_ENDPOINT_MISMATCH` | R4: the named inverse does not run from the target back to the source. |
| `INVERSE_NOT_IDENTITY` | R4: a composition of a morphism with its claimed inverse is not an identity. |
| `INVERTIBLE_WITH_LOSS` | R4: a morphism claimed invertible has a non-empty `lost`. |
| `LOST_NOT_PROPAGATED` | R3: `lost` of a composite lacks what was lost along the way. |
| `PRESERVED_NOT_CARRIED` | R3: a composite claims a property preserved that the steps do not carry through. |
| `RULE_SEAL_FAILED` | R5: the rule reference of a VERIFIED morphism has `SEAL_FAIL`. |
| `SPAN_ON_INELIGIBLE` | R7: a state has a span in a session reported ineligible. |
| `SPAN_ORDER` | R7: a span has p_start < 0 or p_start > p_end, or a generator/composite morphism runs backwards in its session. |
| `UNIT_LAW_VIOLATION` | R2: an explicit unit-law entry does not give the morphism itself. |
| `VERIFIED_ON_REFUTED` | R5: a VERIFIED morphism cites evidence whose validity is REFUTED. |
| `VERIFIED_WITHOUT_EVIDENCE` | R5: a VERIFIED morphism has no evidence, or none that is sealed and checked, or has evidence with a broken seal (v0.4 D-13, D-19). |
| `VERSION_CYCLE` | R6: the chain of versions (`prev_history_hash`) returns to a version already on it (v0.4 D-01). |
