"""cle.grounding.embedding -- the text-to-point-cloud bridge. New code (no
prior CPS equivalent), so tested from scratch rather than ported."""

from __future__ import annotations

import subprocess
import sys

from cle.grounding.embedding import (
    PointCloud,
    char_trigrams,
    embed_text_as_point_cloud,
)


def test_char_trigrams_deterministic_and_sorted() -> None:
    a = char_trigrams("hello world")
    b = char_trigrams("hello world")
    assert a == b
    assert list(a) == sorted(a)


def test_char_trigrams_case_insensitive() -> None:
    assert char_trigrams("ABC") == char_trigrams("abc")


def test_char_trigrams_short_text_returns_normalized_whole_string() -> None:
    assert char_trigrams("ab") == ("ab",)


def test_char_trigrams_empty_text_returns_empty() -> None:
    assert char_trigrams("") == ()
    assert char_trigrams("   ") == ()


def test_embed_empty_text_returns_canonical_origin_point() -> None:
    points = embed_text_as_point_cloud("", dimension=4)
    assert points == ((0.0, 0.0, 0.0, 0.0),)


def test_embed_nonempty_text_returns_one_point_per_trigram() -> None:
    text = "hello world"
    points = embed_text_as_point_cloud(text, dimension=8)
    assert len(points) == len(char_trigrams(text))


def test_embed_vectors_have_requested_dimension() -> None:
    for vector in embed_text_as_point_cloud("some sample text", dimension=6):
        assert len(vector) == 6


def test_embed_vectors_are_unit_normalized() -> None:
    for vector in embed_text_as_point_cloud("some sample text", dimension=8):
        norm = sum(component**2 for component in vector) ** 0.5
        assert abs(norm - 1.0) < 1e-9


def test_shared_trigram_yields_identical_vector_across_different_texts() -> None:
    grams_a = char_trigrams("hello world")
    grams_b = char_trigrams("world hello again")
    shared = set(grams_a) & set(grams_b)
    assert shared, "test setup: the two texts must actually share a trigram"

    points_a = dict(
        zip(grams_a, embed_text_as_point_cloud("hello world", dimension=8), strict=True)
    )
    points_b = dict(
        zip(
            grams_b,
            embed_text_as_point_cloud("world hello again", dimension=8),
            strict=True,
        )
    )
    for gram in shared:
        assert points_a[gram] == points_b[gram]


def test_different_text_produces_different_point_clouds() -> None:
    a = embed_text_as_point_cloud("Japan_Govt", dimension=8)
    b = embed_text_as_point_cloud("Private_Corp", dimension=8)
    assert a != b


def test_embedding_deterministic_within_one_process() -> None:
    text = "軌跡が不安定なので安定化してほしい。"
    assert embed_text_as_point_cloud(text) == embed_text_as_point_cloud(text)


def test_embedding_deterministic_across_processes_and_hash_seeds() -> None:
    """The real proof: unlike Python's `hash()`, SHA-256-based embedding
    must not vary with PYTHONHASHSEED. Spawns two real subprocesses with
    different seeds -- the same class of empirical check
    cognitive-port-selector ran for its own PYTHONHASHSEED fix this
    session, applied here to a genuinely new code path."""
    script = (
        "from cle.grounding.embedding import embed_text_as_point_cloud;"
        "print(embed_text_as_point_cloud('決定論的な検証テキスト', dimension=8))"
    )
    outputs = set()
    for seed in ("1", "2", "3"):
        result = subprocess.run(
            [sys.executable, "-c", script],
            env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin:/usr/local/bin"},
            capture_output=True,
            text=True,
            check=True,
        )
        outputs.add(result.stdout)
    assert len(outputs) == 1, f"embedding varied across PYTHONHASHSEED: {outputs}"


def test_point_cloud_from_text_matches_embed_text_as_point_cloud() -> None:
    cloud = PointCloud.from_text("sample text", dimension=8)
    expected = embed_text_as_point_cloud("sample text", dimension=8)
    assert tuple(point.theta for point in cloud.states) == expected


def test_point_cloud_from_vectors_round_trips() -> None:
    vectors = ((1.0, 0.0), (0.0, 1.0))
    cloud = PointCloud.from_vectors(vectors)
    assert tuple(point.theta for point in cloud.states) == vectors


def test_point_cloud_satisfies_coordinates_of_duck_type() -> None:
    """The actual integration contract: `cle.runtime.engine._coordinates_of`
    must accept a `PointCloud` exactly like it accepts a real
    `StabilizedTrajectoryLike`."""
    from cle.runtime.engine import _coordinates_of

    cloud = PointCloud.from_text("duck type check", dimension=4)
    coordinates = _coordinates_of(cloud)
    assert coordinates == tuple(point.theta for point in cloud.states)
