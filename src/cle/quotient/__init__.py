"""Quotient construction.

Owns collapsing an equivalence class of concepts — as judged by
`cle.homotopy.HomotopyAnalyzer` — into one canonical `Category`. This is how
CLE avoids committing the same knowledge twice under two different
evidence-path identities.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from cle.abi.outputs import Category


@runtime_checkable
class QuotientConstructor(Protocol):
    """An equivalence class of concept ids -> one canonical `Category`."""

    def quotient(self, concept_ids: tuple[str, ...]) -> Category: ...


__all__ = ["QuotientConstructor"]
