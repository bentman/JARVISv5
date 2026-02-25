"""Unit tests for deterministic cache key policy and stable JSON helpers."""
from __future__ import annotations

import math

import pytest

from backend.cache.key_policy import dumps_json, loads_json, make_cache_key


def test_same_logical_input_produces_identical_key() -> None:
    parts = {
        "task_id": "task-123",
        "turn": 2,
        "flags": [True, False, None],
        "meta": {"a": 1, "b": "x"},
    }
    k1 = make_cache_key("context", parts=parts)
    k2 = make_cache_key("context", parts=parts)
    assert k1 == k2


def test_dict_order_does_not_affect_key() -> None:
    p1 = {"b": 2, "a": 1, "c": {"y": 2, "x": 1}}
    p2 = {"c": {"x": 1, "y": 2}, "a": 1, "b": 2}
    assert make_cache_key("embed", parts=p1) == make_cache_key("embed", parts=p2)


def test_hashing_behavior_when_key_exceeds_threshold() -> None:
    long_text = "x" * 1000
    key = make_cache_key("prompt", parts={"text": long_text}, max_key_length=64)
    assert key.startswith("prompt:v1:h:")
    assert len(key.split(":")[-1]) == 64


def test_dumps_json_stability_for_nested_objects() -> None:
    obj1 = {"z": [3, 2, 1], "a": {"b": 2, "a": 1}}
    obj2 = {"a": {"a": 1, "b": 2}, "z": [3, 2, 1]}
    s1 = dumps_json(obj1)
    s2 = dumps_json(obj2)
    assert s1 == s2
    assert loads_json(s1) == loads_json(s2) == {"a": {"a": 1, "b": 2}, "z": [3, 2, 1]}


def test_ascii_only_output_for_non_ascii_input() -> None:
    text = dumps_json({"word": "café"})
    assert "café" not in text
    assert "\\u00e9" in text


def test_non_finite_float_values_rejected() -> None:
    with pytest.raises(ValueError):
        make_cache_key("x", parts={"v": math.nan})
    with pytest.raises(ValueError):
        make_cache_key("x", parts={"v": math.inf})
    with pytest.raises(ValueError):
        make_cache_key("x", parts={"v": -math.inf})
