"""`measure_compression` (spec v2.0.0 §4.3)."""

from __future__ import annotations

from cle.compression import CompressionResult, measure_compression


def test_ratio_meets_target_when_compression_is_at_least_tenfold() -> None:
    raw = "x" * 1000
    lifted = "y" * 10
    result = measure_compression(raw, lifted)
    assert result.ratio >= 10.0
    assert result.meets_target


def test_ratio_below_target_is_reported_as_not_meeting_it() -> None:
    raw = "x" * 20
    lifted = "y" * 10
    result = measure_compression(raw, lifted)
    assert result.ratio < 10.0
    assert not result.meets_target


def test_zero_lifted_size_with_positive_raw_size_is_infinite_ratio() -> None:
    result = CompressionResult(raw_size=1000, lifted_size=0)
    assert result.ratio == float("inf")
    assert result.meets_target


def test_both_sizes_zero_is_a_zero_ratio_not_infinite() -> None:
    result = CompressionResult(raw_size=0, lifted_size=0)
    assert result.ratio == 0.0
    assert not result.meets_target


def test_measure_compression_uses_utf8_byte_length_of_repr() -> None:
    result = measure_compression("", "")
    assert result.raw_size == len(repr("").encode("utf-8"))
    assert result.lifted_size == len(repr("").encode("utf-8"))
