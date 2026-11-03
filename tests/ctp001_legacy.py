"""Migration adapter for properties named in the old form (`c1.modality`).

R9 reads the constraint of a property from the vocabulary's `constraints` entries and
never from its name. The old fixtures (`tests/golden/ctp001/`) and the R9 unit tests
name their properties `<constraint_id>.<field>` and carry no entries, so this adapter
makes the entries explicitly. It is the only place that takes an old name apart.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from typing import Any

from cle.representation import PropertyVocabulary


def legacy_constraints(properties: Iterable[str]) -> tuple[tuple[str, str], ...]:
    """(property, constraint id) for old names: the part before the first dot."""
    return tuple((p, p.split(".", 1)[0]) for p in properties)


def with_legacy_constraints(vocabulary: PropertyVocabulary) -> PropertyVocabulary:
    """The same vocabulary with the entries made from its (old-form) names."""
    return replace(
        vocabulary,
        constraints=legacy_constraints(
            (*vocabulary.properties, *vocabulary.information)
        ),
    )


def legacy_vocabulary(doc: dict[str, Any]) -> PropertyVocabulary:
    """The vocabulary of an old fixture, through the adapter."""
    return with_legacy_constraints(PropertyVocabulary.from_dict(doc["vocabulary"]))
