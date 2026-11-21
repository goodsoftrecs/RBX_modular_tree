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
        for step in range(0, 6):
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
                    2,
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
        for progress in (0.0, 0.25, 0.5, 0.75, 1.0):
            position = [0.0, 0.0, 3.0]
            position[axis] = progress * 4.0
            direction = [0.0, 0.0, 0.2]
            direction[axis] = 1.0
            anchors.append(
                FoliageAnchor(
                    tuple(position), tuple(direction), 0.1, 2, branch_id, progress
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
    progress = [anchors[index].branch_progress for index in selected]
    assert progress[:2] == [0.0, 0.0]
    assert progress == sorted(progress)


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


def test_connections_precede_outward_anchors_with_physical_priority_per_stage():
    anchors = [
        FoliageAnchor((0.0, 0.0, 1.0), (0.0, 0.0, 1.0), 0.5, 0, 0, 1.0),
        FoliageAnchor((0.0, 0.0, 2.0), (1.0, 0.0, 0.0), 0.16, 2, 1, 0.0),
        FoliageAnchor((1.0, 0.0, 2.0), (1.0, 0.0, 0.0), 0.12, 2, 1, 0.5),
        FoliageAnchor((2.0, 0.0, 2.0), (1.0, 0.0, 0.0), 0.08, 2, 1, 1.0),
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

    assert [(anchors[index].branch_id, anchors[index].branch_progress) for index in selected[:2]] == [
        (1, 0.0),
        (2, 0.0),
    ]
    assert anchors[selected[2]].branch_id == 1
    missing_progress = [
        anchors[index].branch_progress
        for index in selected[3:]
        if anchors[index].branch_id == 2
    ]
    assert missing_progress == sorted(missing_progress)


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


def test_scale_multiplier_changes_card_scale_and_automatic_spacing_footprint():
    normal = build_card_layout(_anchors(), cluster_count=5, scale_multiplier=1.0, seed=44)
    doubled = build_card_layout(_anchors(), cluster_count=5, scale_multiplier=2.0, seed=44)

    for original, scaled in zip(normal, doubled, strict=True):
        assert scaled.scale == pytest.approx(original.scale * 2.0)
    assert [placement.anchor_index for placement in normal] != [
        placement.anchor_index for placement in doubled
    ]


def test_branch_spacing_skips_farther_down_one_branch():
    anchors = [
        FoliageAnchor(
            (float(step), 0.0, 2.0),
            (1.0, 0.0, 0.0),
            0.1,
            2,
            1,
            step / 5.0,
        )
        for step in range(0, 6)
    ]

    dense = build_card_layout(
        anchors,
        cluster_count=3,
        scale_multiplier=1.0,
        seed=7,
        branch_spacing=0.1,
        template_footprint=1.0,
    )
    spread = build_card_layout(
        anchors,
        cluster_count=3,
        scale_multiplier=1.0,
        seed=7,
        branch_spacing=3.0,
        template_footprint=1.0,
    )

    dense_progress = [
        anchors[dense[index].anchor_index].branch_progress
        for index in range(0, len(dense), 2)
    ]
    spread_progress = [
        anchors[spread[index].anchor_index].branch_progress
        for index in range(0, len(spread), 2)
    ]
    assert dense_progress == [0.0, 0.2, 0.4]
    assert spread_progress == [0.0, 0.4, 0.8]


def test_tighter_spacing_phase_never_backtracks_toward_connection():
    anchors = [
        FoliageAnchor(
            (float(step), 0.0, 2.0),
            (1.0, 0.0, 0.0),
            0.1,
            2,
            1,
            step / 5.0,
        )
        for step in range(0, 6)
    ]
    anchors.extend(
        FoliageAnchor(
            (20.0 + float(step), 0.0, 2.0),
            (1.0, 0.0, 0.0),
            0.1,
            2,
            2,
            step / 5.0,
        )
        for step in range(0, 6)
    )

    layout = build_card_layout(
        anchors,
        cluster_count=4,
        scale_multiplier=1.0,
        seed=7,
        missing_branch_ids=frozenset({2}),
        branch_spacing=3.0,
        template_footprint=1.0,
    )
    selected = [layout[index].anchor_index for index in range(0, len(layout), 2)]
    physical_progress = [
        anchors[index].branch_progress
        for index in selected
        if anchors[index].branch_id == 1
    ]

    assert physical_progress == sorted(physical_progress)


def test_nearby_secondary_connections_are_kept_as_first_branch_candidates():
    anchors = []
    for branch_id, y in ((1, 0.0), (2, 0.1)):
        for step in range(0, 6):
            anchors.append(
                FoliageAnchor(
                    (float(step), y, 2.0),
                    (1.0, 0.0, 0.0),
                    0.1,
                    2,
                    branch_id,
                    step / 5.0,
                )
            )

    layout = build_card_layout(
        anchors,
        cluster_count=2,
        scale_multiplier=1.0,
        seed=7,
        branch_spacing=3.0,
        template_footprint=1.0,
    )
    selected = [layout[index].anchor_index for index in range(0, len(layout), 2)]

    assert [anchors[index].branch_progress for index in selected] == [0.0, 0.0]


def test_branch_card_length_and_variation_are_deterministic_and_bounded():
    uniform = build_card_layout(
        _anchors(),
        cluster_count=8,
        scale_multiplier=1.0,
        seed=91,
        branch_card_length=1.5,
        length_variation=0.0,
    )
    varied = build_card_layout(
        _anchors(),
        cluster_count=8,
        scale_multiplier=1.0,
        seed=91,
        branch_card_length=1.5,
        length_variation=0.5,
    )
    repeated = build_card_layout(
        _anchors(),
        cluster_count=8,
        scale_multiplier=1.0,
        seed=91,
        branch_card_length=1.5,
        length_variation=0.5,
    )

    assert all(placement.length_scale == 1.5 for placement in uniform)
    assert varied == repeated
    assert [placement.anchor_index for placement in varied] == [
        placement.anchor_index for placement in uniform
    ]
    for index in range(0, len(varied), 2):
        pair = varied[index : index + 2]
        assert pair[0].length_scale == pair[1].length_scale
        assert 0.75 <= pair[0].length_scale <= 2.25
    assert any(placement.length_scale != 1.5 for placement in varied)


def test_primary_secondary_mode_prioritizes_trunk_connections_then_secondary_connections():
    anchors = []
    for branch_id, depth, y in ((1, 1, 0.0), (2, 1, 2.0), (3, 2, 4.0), (4, 2, 6.0)):
        for step in range(0, 4):
            anchors.append(
                FoliageAnchor(
                    (float(step), y, 3.0),
                    (1.0, 0.0, 0.0),
                    0.1,
                    depth,
                    branch_id,
                    step / 3.0,
                )
            )

    layout = build_card_layout(
        anchors,
        cluster_count=6,
        scale_multiplier=1.0,
        seed=17,
        include_primary_connections=True,
        primary_card_length=2.5,
        branch_card_length=1.5,
        branch_spacing=0.1,
    )
    selected = [layout[index] for index in range(0, len(layout), 2)]
    selected_anchors = [anchors[placement.anchor_index] for placement in selected]

    assert [anchor.hierarchy_depth for anchor in selected_anchors[:2]] == [1, 1]
    assert [anchor.branch_progress for anchor in selected_anchors[:4]] == [0.0] * 4
    assert [anchor.hierarchy_depth for anchor in selected_anchors[2:4]] == [2, 2]
    assert all(
        placement.length_scale
        == (2.5 if anchor.hierarchy_depth == 1 else 1.5)
        for placement, anchor in zip(selected, selected_anchors, strict=True)
    )
    assert all(anchor.branch_progress > 0.0 for anchor in selected_anchors[4:])


def test_secondary_only_mode_excludes_primary_branch_anchors():
    anchors = []
    for branch_id, depth, y in ((1, 1, 0.0), (2, 2, 2.0)):
        for step in range(0, 4):
            anchors.append(
                FoliageAnchor(
                    (float(step), y, 3.0),
                    (1.0, 0.0, 0.0),
                    0.1,
                    depth,
                    branch_id,
                    step / 3.0,
                )
            )

    layout = build_card_layout(
        anchors,
        cluster_count=4,
        scale_multiplier=1.0,
        seed=17,
        include_primary_connections=False,
    )

    assert all(
        anchors[layout[index].anchor_index].hierarchy_depth >= 2
        for index in range(0, len(layout), 2)
    )


def test_top_tip_pair_uses_highest_terminal_trunk_anchor_before_branch_clusters():
    anchors = _anchors()
    anchors.extend(
        (
            FoliageAnchor(
                (2.0, 0.0, 8.0),
                (0.0, 0.0, 1.0),
                0.4,
                0,
                90,
                0.5,
            ),
            FoliageAnchor(
                (2.0, 0.0, 12.0),
                (0.0, 0.0, 1.0),
                0.2,
                0,
                90,
                1.0,
            ),
        )
    )

    layout = build_card_layout(
        anchors,
        cluster_count=4,
        scale_multiplier=1.0,
        seed=17,
        top_tip_pairs=1,
    )
    selected = [layout[index].anchor_index for index in range(0, len(layout), 2)]

    assert len(layout) == 8
    assert selected[0] == len(anchors) - 1
    assert anchors[selected[0]].hierarchy_depth == 0
    assert all(anchors[index].hierarchy_depth >= 2 for index in selected[1:])


def test_two_top_tip_pairs_share_attachment_and_second_is_rolled_ninety_degrees():
    layout = build_card_layout(
        _anchors(),
        cluster_count=4,
        scale_multiplier=1.0,
        seed=91,
        top_tip_pairs=2,
        branch_card_length=2.25,
        length_variation=0.25,
    )
    first_pair = layout[0:2]
    second_pair = layout[2:4]

    assert first_pair[0].anchor_index == second_pair[0].anchor_index
    assert first_pair[0].position == second_pair[0].position
    assert first_pair[0].length_scale == first_pair[1].length_scale
    assert second_pair[0].length_scale == second_pair[1].length_scale
    assert 1.6875 <= first_pair[0].length_scale <= 2.8125
    assert 1.6875 <= second_pair[0].length_scale <= 2.8125
    assert _dot(first_pair[0].normal, second_pair[0].normal) == pytest.approx(
        0.0, abs=1e-6
    )
    for pair in (first_pair, second_pair):
        angle = math.degrees(
            math.acos(max(-1.0, min(1.0, _dot(pair[0].normal, pair[1].normal))))
        )
        assert angle == pytest.approx(55.0)


def test_top_tip_pairs_are_inside_exact_count_and_zero_disables_them():
    disabled = build_card_layout(
        _anchors(),
        cluster_count=1,
        scale_multiplier=1.0,
        seed=3,
        top_tip_pairs=0,
    )
    clamped = build_card_layout(
        _anchors(),
        cluster_count=1,
        scale_multiplier=1.0,
        seed=3,
        top_tip_pairs=2,
    )

    assert len(disabled) == len(clamped) == 2
    assert _anchors()[disabled[0].anchor_index].hierarchy_depth >= 2
    assert _anchors()[clamped[0].anchor_index].hierarchy_depth == 0


def test_texture_rotation_expands_sampling_uvs_for_clipped_fit():
    corners = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))

    assert [rotate_uv_to_fit(uv, 0.0) for uv in corners] == list(corners)
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
    with pytest.raises(ValueError, match="Branch Spacing"):
        build_card_layout(
            _anchors(), cluster_count=1, scale_multiplier=1.0, seed=0, branch_spacing=0.0
        )
    with pytest.raises(ValueError, match="Branch Card Length"):
        build_card_layout(
            _anchors(),
            cluster_count=1,
            scale_multiplier=1.0,
            seed=0,
            branch_card_length=3.1,
        )
    with pytest.raises(ValueError, match="Primary Card Length"):
        build_card_layout(
            _anchors(),
            cluster_count=1,
            scale_multiplier=1.0,
            seed=0,
            primary_card_length=4.1,
        )
    with pytest.raises(ValueError, match="Length Variation"):
        build_card_layout(
            _anchors(),
            cluster_count=1,
            scale_multiplier=1.0,
            seed=0,
            length_variation=0.51,
        )
    with pytest.raises(ValueError, match="Top Tip Pairs"):
        build_card_layout(
            _anchors(),
            cluster_count=1,
            scale_multiplier=1.0,
            seed=0,
            top_tip_pairs=3,
        )
    with pytest.raises(ValueError, match="Texture rotation"):
        rotate_uv_to_fit((0.0, 0.0), float("inf"))
    with pytest.raises(ValueError, match="Canopy rotation"):
        rotate_card_layout_about_z([], float("nan"))
