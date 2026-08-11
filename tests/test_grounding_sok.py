"""S/O/K(t) triangulation -- relocated from cognitive-port-selector."""

from __future__ import annotations

from cle.grounding.five_w1h import FiveW1HOverrides, extract_five_w1h
from cle.grounding.sok import SOKOverrides, build_sok, detect_shift


def _five_w1h(who: str | None = None):  # type: ignore[no-untyped-def]
    return extract_five_w1h("prompt", "goal", FiveW1HOverrides(who=who))


def test_explicit_subject_override_wins() -> None:
    sok = build_sok(_five_w1h(), SOKOverrides(subject="explicit-subject"))
    assert sok.subject == "explicit-subject"
    assert sok.subject_source == "explicit"


def test_subject_derives_from_five_w1h_who() -> None:
    sok = build_sok(_five_w1h(who="derived-who"))
    assert sok.subject == "derived-who"
    assert sok.subject_source == "derived"


def test_subject_unspecified_without_signal() -> None:
    sok = build_sok(_five_w1h())
    assert sok.subject == "unspecified"
    assert sok.subject_source == "unspecified"


def test_observer_defaults_to_cle() -> None:
    sok = build_sok(_five_w1h())
    assert sok.observer == "CLE"
    assert sok.observer_source == "derived"


def test_observer_explicit_override() -> None:
    sok = build_sok(_five_w1h(), SOKOverrides(observer="a-different-observer"))
    assert sok.observer == "a-different-observer"
    assert sok.observer_source == "explicit"


def test_knowledge_reference_explicit_override() -> None:
    sok = build_sok(_five_w1h(), SOKOverrides(knowledge_reference="explicit-ref"))
    assert sok.knowledge_reference == "explicit-ref"
    assert sok.knowledge_reference_source == "explicit"


def test_knowledge_reference_uses_default_when_no_override() -> None:
    sok = build_sok(_five_w1h(), default_knowledge_reference="default-ref")
    assert sok.knowledge_reference == "default-ref"
    assert sok.knowledge_reference_source == "derived"


def test_knowledge_reference_unspecified_without_default() -> None:
    sok = build_sok(_five_w1h())
    assert sok.knowledge_reference == "unspecified"
    assert sok.knowledge_reference_source == "unspecified"


def test_detect_shift_subject_only() -> None:
    before = build_sok(_five_w1h(), SOKOverrides(subject="A"))
    after = build_sok(_five_w1h(), SOKOverrides(subject="B"))
    assert detect_shift(before, after) == ("subject",)


def test_detect_shift_observer_only() -> None:
    before = build_sok(_five_w1h(), SOKOverrides(observer="A"))
    after = build_sok(_five_w1h(), SOKOverrides(observer="B"))
    assert detect_shift(before, after) == ("observer",)


def test_detect_shift_knowledge_reference_only() -> None:
    before = build_sok(_five_w1h(), SOKOverrides(knowledge_reference="A"))
    after = build_sok(_five_w1h(), SOKOverrides(knowledge_reference="B"))
    assert detect_shift(before, after) == ("knowledge_reference",)


def test_detect_shift_no_change() -> None:
    state = build_sok(
        _five_w1h(), SOKOverrides(subject="A", observer="B", knowledge_reference="C")
    )
    assert detect_shift(state, state) == ()
