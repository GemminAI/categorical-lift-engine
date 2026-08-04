"""One conformance test per owned stage: a minimal fake satisfies each Protocol.

These exist to keep every stage module import-clean and to document, by
example, the smallest possible implementation of each interface — not to
assert anything about categorical-theory correctness, which this repository
does not implement (see `docs/RFC_ALIGNMENT.md`).
"""

from __future__ import annotations

from cle.abi.outputs import Category, CategoryRelation, Concept, ConceptDelta
from cle.category import CategoryConstructor
from cle.commit_candidate import CommitCandidateBuilder
from cle.concept import ConceptDiscoveryStrategy
from cle.crystallization import KnowledgeCrystallizer
from cle.functor import FunctorConstructor
from cle.homotopy import HomotopyAnalyzer
from cle.knowledge_delta import KnowledgeDeltaGenerator
from cle.natural_transformation import NaturalTransformationAnalyzer
from cle.quotient import QuotientConstructor


def test_concept_discovery_strategy_is_satisfied_by_shape() -> None:
    class Fake:
        def discover(self, trajectory: object, *, hekb_context: object) -> Concept:
            raise NotImplementedError

    assert isinstance(Fake(), ConceptDiscoveryStrategy)


def test_category_constructor_is_satisfied_by_shape() -> None:
    class Fake:
        def construct(self, artifact: object, *, hekb_context: object) -> None:
            return None

    assert isinstance(Fake(), CategoryConstructor)


def test_homotopy_analyzer_is_satisfied_by_shape() -> None:
    class Fake:
        def is_homotopic(self, a: object, b: object) -> bool:
            return False

    assert isinstance(Fake(), HomotopyAnalyzer)


def test_quotient_constructor_is_satisfied_by_shape() -> None:
    class Fake:
        def quotient(self, concept_ids: tuple[str, ...]) -> Category:
            raise NotImplementedError

    assert isinstance(Fake(), QuotientConstructor)


def test_functor_constructor_is_satisfied_by_shape() -> None:
    class Fake:
        def construct(self, source: Category, target: Category) -> CategoryRelation:
            raise NotImplementedError

    assert isinstance(Fake(), FunctorConstructor)


def test_natural_transformation_analyzer_is_satisfied_by_shape() -> None:
    class Fake:
        def analyze(self, source: CategoryRelation, target: CategoryRelation) -> None:
            return None

    assert isinstance(Fake(), NaturalTransformationAnalyzer)


def test_knowledge_crystallizer_is_satisfied_by_shape() -> None:
    class Fake:
        def crystallize(self, artifact: object) -> object:
            return artifact

    assert isinstance(Fake(), KnowledgeCrystallizer)


def test_knowledge_delta_generator_is_satisfied_by_shape() -> None:
    class Fake:
        def generate(self, artifact: object) -> object:
            raise NotImplementedError

    assert isinstance(Fake(), KnowledgeDeltaGenerator)


def test_commit_candidate_builder_is_satisfied_by_shape() -> None:
    class Fake:
        def build(self, delta: object, *, source_trajectory_id: str) -> object:
            raise NotImplementedError

    assert isinstance(Fake(), CommitCandidateBuilder)


def test_concept_delta_is_a_valid_artifact_shape() -> None:
    # ConceptDelta participates in the same Artifact union as Concept; this
    # just confirms it constructs without a discovered Concept in hand.
    delta = ConceptDelta(concept_id="c-1", frame_id="F", centroid_shift=(0.1, 0.1))
    assert delta.reinforcement_count == 1
