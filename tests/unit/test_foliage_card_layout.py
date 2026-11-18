"""Tests for deterministic branch-aligned shallow-V foliage cards."""

import math

import pytest

from foliage_anchor_data import FoliageAnchor
from foliage_card_layout import build_card_layout, eligible_anchor_indices


def _anchors():
    anchors = [
        FoliageAnchor((0.0, 0.0, z), (0.0, 0.0, 1.0), 1.0 - z * 0.03, 0, 0, z / 10.0)
        for z in range(1, 10)
    ]
    for branch_id, angle in enumerate((0.0, 1.57, 3.14, 4.71), start=1):
        for step in range(1, 6):
            radius = 0.32 - step * 0.045
            direction = (math.cos(angle), math.sin(angle), 0.25)
            anchors.append(
                FoliageAnchor(
                    (
                        math.cos(angle) * step * 1.4,
                        math.sin(angle) * step * 1.4,
                        4.0 + step * 0.6,
                    ),
                    direction,
                    radius,
                    1 + (step >= 4),
                    branch_id,
                    step / 5.0,
                )
            )
    return anchors


def _dot(a, b):
    return sum(first * second for first, second in zip(a, b, strict=True))


def test_layout_is_deterministic_and_returns_exact_card_count():
    first = build_card_layout(_anchors(), cluster_count=8, scale_multiplier=1.0, seed=538)
    second = build_card_layout(_anchors(), cluster_count=8, scale_multiplier=1.0, seed=538)

    assert first == second
    assert len(first) == 16
    assert {placement.cluster_index for placement in first} == set(range(8))


def test_trunk_and_thick_branch_bases_are_ineligible():
    anchors = _anchors()
    eligible = eligible_anchor_indices(anchors)

    assert all(anchors[index].hierarchy_depth > 0 for index in eligible)
    assert all(anchors[index].branch_progress >= 0.2 for index in eligible)
    assert len(eligible) < len(anchors)


def test_each_pair_follows_branch_and_forms_fixed_v_angle():
    layout = build_card_layout(_anchors(), cluster_count=6, scale_multiplier=1.0, seed=12)

    for index in range(0, len(layout), 2):
        first, second = layout[index : index + 2]
        assert first.anchor_index == second.anchor_index
        assert first.direction == second.direction
        assert abs(_dot(first.normal, first.direction)) < 1e-6
        assert abs(_dot(second.normal, second.direction)) < 1e-6
        angle = math.degrees(math.acos(max(-1.0, min(1.0, _dot(first.normal, second.normal)))))
        assert angle == pytest.approx(55.0)


def test_scale_multiplier_only_changes_card_scale():
    normal = build_card_layout(_anchors(), cluster_count=5, scale_multiplier=1.0, seed=44)
    doubled = build_card_layout(_anchors(), cluster_count=5, scale_multiplier=2.0, seed=44)

    assert [placement.anchor_index for placement in normal] == [
        placement.anchor_index for placement in doubled
    ]
    for original, scaled in zip(normal, doubled, strict=True):
        assert scaled.scale == pytest.approx(original.scale * 2.0)


def test_invalid_layout_inputs_fail_explicitly():
    with pytest.raises(ValueError, match="count"):
        build_card_layout(_anchors(), cluster_count=0, scale_multiplier=1.0, seed=0)
    with pytest.raises(ValueError, match="scale"):
        build_card_layout(_anchors(), cluster_count=1, scale_multiplier=0.0, seed=0)
