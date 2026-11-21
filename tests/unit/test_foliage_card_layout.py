"""Tests for deterministic branch-aligned shallow-V foliage cards."""

import math

import pytest

from foliage_anchor_data import FoliageAnchor
from foliage_card_layout import (
    build_card_layout,
    classify_missing_branch_ids,
    eligible_anchor_indices,
    rotate_card_layout_about_z,
    rotate_uv_to_fit,
    rotate_uv_within_bounds,
)


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


def test_count_increase_is_stable_prefix_and_fills_visible_branches_inward():
    anchors = []
    for branch_id, axis in ((1, 0), (2, 1)):
        for progress in (0.25, 0.5, 0.75, 1.0):
            position = [0.0, 0.0, 3.0]
            position[axis] = progress * 4.0
            direction = [0.0, 0.0, 0.2]
            direction[axis] = 1.0
            anchors.append(
                FoliageAnchor(
                    tuple(position), tuple(direction), 0.1, 1, branch_id, progress
                )
            )

    lower = build_card_layout(
        anchors,
        cluster_count=4,
        scale_multiplier=1.0,
        seed=538,
        template_slots=(1, 2, 3, 4),
    )
    higher = build_card_layout(
        anchors,
        cluster_count=6,
        scale_multiplier=1.0,
        seed=538,
        template_slots=(1, 2, 3, 4),
    )

    assert higher[: len(lower)] == lower
    selected = [higher[index].anchor_index for index in range(0, len(higher), 2)]
    assert [anchors[index].branch_progress for index in selected] == [
        1.0,
        1.0,
        0.75,
        0.75,
        0.5,
        0.5,
    ]


def test_geometric_detection_uses_middle_and_outer_branch_path():
    anchors = [
        FoliageAnchor((0.0, 0.0, 1.0), (0.0, 0.0, 1.0), 0.5, 0, 0, 1.0),
        FoliageAnchor((1.0, 0.0, 2.0), (1.0, 0.0, 0.0), 0.15, 1, 1, 0.2),
        FoliageAnchor((2.0, 0.0, 2.0), (1.0, 0.0, 0.0), 0.10, 1, 1, 0.6),
        FoliageAnchor((3.0, 0.0, 2.0), (1.0, 0.0, 0.0), 0.05, 1, 1, 1.0),
        FoliageAnchor((0.0, 1.0, 2.0), (0.0, 1.0, 0.0), 0.15, 1, 2, 0.2),
        FoliageAnchor((0.0, 2.0, 2.0), (0.0, 1.0, 0.0), 0.10, 1, 2, 0.6),
        FoliageAnchor((0.0, 3.0, 2.0), (0.0, 1.0, 0.0), 0.05, 1, 2, 1.0),
    ]

    def distance_to_wood(position):
        # Both branches touch wood near their bases, but only branch 1 follows wood outward.
        if position[0] >= 1.5:
            return 0.08
        if position[1] >= 1.5:
            return 2.0
        return 0.05

    assert classify_missing_branch_ids(anchors, distance_to_wood, 10.0) == {2}


def test_physical_branches_precede_missing_branches_then_missing_runs_outward():
    anchors = [
        FoliageAnchor((0.0, 0.0, 1.0), (0.0, 0.0, 1.0), 0.5, 0, 0, 1.0),
        FoliageAnchor((1.0, 0.0, 2.0), (1.0, 0.0, 0.0), 0.12, 1, 1, 0.5),
        FoliageAnchor((2.0, 0.0, 2.0), (1.0, 0.0, 0.0), 0.08, 1, 1, 1.0),
        FoliageAnchor((0.2, 0.0, 2.0), (0.0, 1.0, 0.0), 0.18, 2, 2, 0.0),
        FoliageAnchor((0.2, 1.0, 2.0), (0.0, 1.0, 0.0), 0.10, 2, 2, 0.5),
        FoliageAnchor((0.2, 2.0, 2.0), (0.0, 1.0, 0.0), 0.05, 2, 2, 1.0),
    ]
    layout = build_card_layout(
        anchors,
        cluster_count=5,
        scale_multiplier=1.0,
        seed=21,
        missing_branch_ids=frozenset({2}),
    )
    selected = [layout[index].anchor_index for index in range(0, len(layout), 2)]

    assert all(anchors[index].branch_id == 1 for index in selected[:2])
    missing_progress = [anchors[index].branch_progress for index in selected[2:]]
    assert missing_progress == sorted(missing_progress)
    assert missing_progress[0] == 0.0


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


def test_texture_rotation_expands_sampling_uvs_for_clipped_fit():
    corners = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))

    assert [rotate_uv_to_fit(uv, 0.0) for uv in corners] == corners
    rotated = [rotate_uv_to_fit(uv, math.radians(45.0)) for uv in corners]

    assert any(component < 0.0 for uv in rotated for component in uv)
    assert any(component > 1.0 for uv in rotated for component in uv)
    assert rotated != list(corners)


def test_atlas_texture_rotation_remains_inside_assigned_quadrant():
    bounds = (0.5, 0.5, 1.0, 1.0)
    corners = ((0.5, 0.5), (1.0, 0.5), (1.0, 1.0), (0.5, 1.0))
    rotated = [
        rotate_uv_within_bounds(uv, math.radians(45.0), bounds) for uv in corners
    ]

    assert rotated != list(corners)
    assert all(0.5 <= u <= 1.0 and 0.5 <= v <= 1.0 for u, v in rotated)


def test_four_template_variants_use_balanced_deterministic_pairs():
    first = build_card_layout(
        _anchors(),
        cluster_count=10,
        scale_multiplier=1.0,
        seed=538,
        template_slots=(1, 2, 3, 4),
    )
    second = build_card_layout(
        _anchors(),
        cluster_count=10,
        scale_multiplier=1.0,
        seed=538,
        template_slots=(1, 2, 3, 4),
    )

    assert first == second
    cluster_slots = []
    for index in range(0, len(first), 2):
        pair = first[index : index + 2]
        assert pair[0].template_slot == pair[1].template_slot
        cluster_slots.append(pair[0].template_slot)
    counts = {slot: cluster_slots.count(slot) for slot in range(1, 5)}
    assert max(counts.values()) - min(counts.values()) <= 1


def test_pair_rotation_rolls_cards_without_changing_selection_or_v_angle():
    normal = build_card_layout(_anchors(), cluster_count=6, scale_multiplier=1.0, seed=12)
    rolled = build_card_layout(
        _anchors(),
        cluster_count=6,
        scale_multiplier=1.0,
        seed=12,
        pair_rotation_radians=math.radians(90.0),
    )

    for original, rotated in zip(normal, rolled, strict=True):
        assert rotated.anchor_index == original.anchor_index
        assert rotated.position == original.position
        assert rotated.direction == original.direction
        assert rotated.scale == original.scale
        assert _dot(rotated.normal, original.normal) == pytest.approx(0.0, abs=1e-6)

    for index in range(0, len(rolled), 2):
        first, second = rolled[index : index + 2]
        angle = math.degrees(math.acos(max(-1.0, min(1.0, _dot(first.normal, second.normal)))))
        assert angle == pytest.approx(55.0)


def test_canopy_rotation_moves_positions_and_axes_about_local_z():
    layout = build_card_layout(_anchors(), cluster_count=4, scale_multiplier=1.0, seed=3)
    rotated = rotate_card_layout_about_z(layout, math.radians(90.0))

    for original, transformed in zip(layout, rotated, strict=True):
        assert transformed.position == pytest.approx(
            (-original.position[1], original.position[0], original.position[2])
        )
        assert transformed.direction == pytest.approx(
            (-original.direction[1], original.direction[0], original.direction[2])
        )
        assert transformed.normal == pytest.approx(
            (-original.normal[1], original.normal[0], original.normal[2])
        )
        assert transformed.scale == original.scale


def test_invalid_layout_inputs_fail_explicitly():
    with pytest.raises(ValueError, match="count"):
        build_card_layout(_anchors(), cluster_count=0, scale_multiplier=1.0, seed=0)
    with pytest.raises(ValueError, match="scale"):
        build_card_layout(_anchors(), cluster_count=1, scale_multiplier=0.0, seed=0)
    with pytest.raises(ValueError, match="pair rotation"):
        build_card_layout(
            _anchors(),
            cluster_count=1,
            scale_multiplier=1.0,
            seed=0,
            pair_rotation_radians=float("nan"),
        )
    with pytest.raises(ValueError, match="Texture rotation"):
        rotate_uv_to_fit((0.0, 0.0), float("inf"))
    with pytest.raises(ValueError, match="Canopy rotation"):
        rotate_card_layout_about_z([], float("nan"))
