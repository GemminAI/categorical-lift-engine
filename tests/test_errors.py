from __future__ import annotations

import pytest

from cle.errors import CLEError, DimensionMismatch, NoStrategyConfigured, NotStabilized


@pytest.mark.parametrize(
    "exception_type", [DimensionMismatch, NoStrategyConfigured, NotStabilized]
)
def test_every_cle_error_derives_from_cle_error(exception_type: type[CLEError]) -> None:
    assert issubclass(exception_type, CLEError)


def test_cle_error_is_an_exception() -> None:
    assert issubclass(CLEError, Exception)
