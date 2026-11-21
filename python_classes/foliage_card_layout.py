"""Pure deterministic selection and shallow-V layout for foliage cards."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace
from typing import Callable

try:
    from .foliage_anchor_data import FoliageAnchor, validate_anchor
except ImportError:  # Pure unit tests import this module outside the Blender package.
    from foliage_anchor_data import FoliageAnchor, validate_anchor


DEFAULT_V_ANGLE_DEGREES = 55.0
DEFAULT_SCALE_REFERENCE_CLUSTERS = 30
_SPACING_PHASE_FACTORS = (1.0, 0.75, 0.5, 0.25, 0.0)


@dataclass(frozen=True)
class CardPlacement:
    """Transform inputs for one card whose local long axis is positive Z."""

    cluster_index: int
    card_index: int
    anchor_index: int
    position: tuple[float, float, float]
    direction: tuple[float, float, float]
    normal: tuple[float, float, float]
    scale: float
    length_scale: float = 1.0
    template_slot: int = 1
    is_top_tip: bool = False


def _length(vector: tuple[float, float, float]) -> float:
    return math.sqrt(sum(component * component for component in vector))


def _normalize(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    length = _length(vector)
    if length <= 1e-12:
        raise ValueError("Cannot normalize a zero-length vector")
    return tuple(component / length for component in vector)


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum(first * second for first, second in zip(a, b, strict=True))


def _cross(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _rotate_about_axis(
    vector: tuple[float, float, float],
    axis: tuple[float, float, float],
    angle: float,
) -> tuple[float, float, float]:
    cosine = math.cos(angle)
    sine = math.sin(angle)
    cross = _cross(axis, vector)
    dot = _dot(axis, vector)
    return tuple(
        vector[index] * cosine
        + cross[index] * sine
        + axis[index] * dot * (1.0 - cosine)
        for index in range(3)
    )


def rotate_uv_to_fit(
    uv: tuple[float, float], angle_radians: float
) -> tuple[float, float]:
    """Return clipped sampling UVs that rotate and fit the full texture inside the card."""

    if not math.isfinite(angle_radians):
        raise ValueError("Texture rotation must be finite")
    sample_angle = -angle_radians
    cosine = math.cos(sample_angle)
    sine = math.sin(sample_angle)
    sampling_scale = max(abs(cosine) + abs(sine), 1.0)
    centered_u = (float(uv[0]) - 0.5) * sampling_scale
    centered_v = (float(uv[1]) - 0.5) * sampling_scale
    return (
        0.5 + centered_u * cosine - centered_v * sine,
        0.5 + centered_u * sine + centered_v * cosine,
    )


def rotate_uv_within_bounds(
    uv: tuple[float, float],
    angle_radians: float,
    bounds: tuple[float, float, float, float],
) -> tuple[float, float]:
    """Rotate an atlas UV without allowing sampling to escape its assigned cell."""

    if not math.isfinite(angle_radians):
        raise ValueError("Texture rotation must be finite")
    minimum_u, minimum_v, maximum_u, maximum_v = bounds
    width = maximum_u - minimum_u
    height = maximum_v - minimum_v
    if width <= 0.0 or height <= 0.0:
        raise ValueError("Atlas UV bounds must have positive width and height")

    normalized_u = (float(uv[0]) - minimum_u) / width
    normalized_v = (float(uv[1]) - minimum_v) / height
    if not (-1e-6 <= normalized_u <= 1.0 + 1e-6) or not (
        -1e-6 <= normalized_v <= 1.0 + 1e-6
    ):
        raise ValueError("Template UV lies outside its assigned atlas cell")

    sample_angle = -angle_radians
    cosine = math.cos(sample_angle)
    sine = math.sin(sample_angle)
    sampling_scale = 1.0 / max(abs(cosine) + abs(sine), 1.0)
    centered_u = (normalized_u - 0.5) * sampling_scale
    centered_v = (normalized_v - 0.5) * sampling_scale
    rotated_u = 0.5 + centered_u * cosine - centered_v * sine
    rotated_v = 0.5 + centered_u * sine + centered_v * cosine
    return (
        minimum_u + min(1.0, max(0.0, rotated_u)) * width,
        minimum_v + min(1.0, max(0.0, rotated_v)) * height,
    )


def _template_slots_for_clusters(
    cluster_count: int, template_slots: tuple[int, ...], seed: int
) -> list[int]:
    """Return balanced deterministic shuffled cycles without perturbing anchor RNG."""

    if not template_slots or any(slot < 1 for slot in template_slots):
        raise ValueError("At least one positive foliage template slot is required")
    rng = random.Random(int(seed) ^ 0x6D2B79F5)
    assigned: list[int] = []
    while len(assigned) < cluster_count:
        cycle = list(template_slots)
        rng.shuffle(cycle)
        assigned.extend(cycle)
    return assigned[:cluster_count]


def rotate_card_layout_about_z(
    placements: list[CardPlacement], angle_radians: float
) -> list[CardPlacement]:
    """Rotate a complete placement set around the tree-local Z axis."""

    if not math.isfinite(angle_radians):
        raise ValueError("Canopy rotation must be finite")
    if abs(angle_radians) <= 1e-12:
        return placements.copy()
    axis = (0.0, 0.0, 1.0)
    return [
        replace(
            placement,
            position=_rotate_about_axis(placement.position, axis, angle_radians),
            direction=_normalize(
                _rotate_about_axis(placement.direction, axis, angle_radians)
            ),
            normal=_normalize(_rotate_about_axis(placement.normal, axis, angle_radians)),
        )
        for placement in placements
    ]


def _distance_squared(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> float:
    return sum((first - second) ** 2 for first, second in zip(a, b, strict=True))


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def eligible_anchor_indices(
    anchors: list[FoliageAnchor],
    missing_branch_ids: frozenset[int] = frozenset(),
) -> list[int]:
    """Exclude trunk, branch bases, and the thickest interior graph locations."""

    validated = [validate_anchor(anchor) for anchor in anchors]
    branch_anchors = [anchor for anchor in validated if anchor.hierarchy_depth > 0]
    if not branch_anchors:
        raise ValueError("Complete tree graph has no non-trunk foliage anchors")

    radius_cutoff = _percentile([anchor.radius for anchor in branch_anchors], 0.82)
    eligible = [
        index
        for index, anchor in enumerate(validated)
        if anchor.hierarchy_depth > 0
        and (
            anchor.branch_id in missing_branch_ids
            or (
                anchor.branch_progress >= 0.2
                and anchor.radius <= radius_cutoff + 1e-9
            )
        )
    ]
    if not eligible:
        raise ValueError("Complete tree graph has no eligible outer foliage anchors")
    return eligible


def foliage_branch_candidate_indices(
    anchors: list[FoliageAnchor],
    missing_branch_ids: frozenset[int] = frozenset(),
    *,
    include_primary_connections: bool = False,
) -> list[int]:
    """Return candidates for foliage-bearing primary and/or secondary branches."""

    validated = [validate_anchor(anchor) for anchor in anchors]
    minimum_depth = 1 if include_primary_connections else 2
    branch_rows = [
        (index, anchor)
        for index, anchor in enumerate(validated)
        if anchor.hierarchy_depth >= minimum_depth
    ]
    if not branch_rows:
        layer_name = "primary or secondary" if include_primary_connections else "secondary"
        raise ValueError(f"Complete tree graph has no {layer_name} foliage branches")

    outer = [anchor for _, anchor in branch_rows if anchor.branch_progress >= 0.2]
    if not outer:
        raise ValueError("Foliage branches have no outward anchors")
    radius_cutoff = _percentile([anchor.radius for anchor in outer], 0.82)

    branches: dict[int, list[int]] = {}
    for index, anchor in branch_rows:
        branches.setdefault(anchor.branch_id, []).append(index)

    candidates: list[int] = []
    for branch_id in sorted(branches):
        indices = sorted(
            branches[branch_id],
            key=lambda index: (validated[index].branch_progress, index),
        )
        roots = [
            index
            for index in indices
            if validated[index].branch_progress <= 1e-6
        ]
        branch_outer = [
            index
            for index in indices
            if validated[index].branch_progress >= 0.2
            and (
                branch_id in missing_branch_ids
                or validated[index].radius <= radius_cutoff + 1e-9
            )
        ]
        if not roots or not branch_outer:
            continue
        candidates.append(roots[0])
        candidates.extend(branch_outer)

    if not candidates:
        raise ValueError(
            "Complete tree graph has no foliage-bearing branch connections"
        )
    return candidates


def secondary_branch_candidate_indices(
    anchors: list[FoliageAnchor],
    missing_branch_ids: frozenset[int] = frozenset(),
) -> list[int]:
    """Compatibility wrapper for secondary-only candidate selection."""

    return foliage_branch_candidate_indices(anchors, missing_branch_ids)


def classify_missing_branch_ids(
    anchors: list[FoliageAnchor],
    distance_to_wood: Callable[[tuple[float, float, float]], float],
    tree_extent: float,
) -> set[int]:
    """Infer omitted branches from the middle/outer path's distance to final wood."""

    if not math.isfinite(tree_extent) or tree_extent <= 0.0:
        raise ValueError("Tree extent must be finite and greater than zero")
    validated = [validate_anchor(anchor) for anchor in anchors]
    branches: dict[int, list[FoliageAnchor]] = {}
    for anchor in validated:
        if anchor.hierarchy_depth <= 0:
            continue
        branches.setdefault(anchor.branch_id, []).append(anchor)

    missing: set[int] = set()
    minimum_tolerance = tree_extent * 0.0125
    for branch_id, branch_anchors in branches.items():
        ordered = sorted(branch_anchors, key=lambda anchor: anchor.branch_progress)
        samples = [anchor for anchor in ordered if anchor.branch_progress >= 0.45]
        if not samples:
            samples = [ordered[-1]]
        near_count = 0
        for anchor in samples:
            distance = float(distance_to_wood(anchor.position))
            if not math.isfinite(distance) or distance < 0.0:
                raise ValueError("Wood-distance query returned an invalid distance")
            tolerance = max(minimum_tolerance, anchor.radius * 2.5)
            if distance <= tolerance:
                near_count += 1
        if near_count * 2 < len(samples):
            missing.add(branch_id)
    return missing


def _anchor_scores(
    anchors: list[FoliageAnchor], eligible: list[int]
) -> dict[int, float]:
    positions = [anchors[index].position for index in eligible]
    center = tuple(
        sum(position[axis] for position in positions) / len(positions) for axis in range(3)
    )
    radial = {
        index: math.sqrt(_distance_squared(anchors[index].position, center)) for index in eligible
    }
    maximum_radial = max(max(radial.values()), 1e-6)
    maximum_depth = max(max(anchors[index].hierarchy_depth for index in eligible), 1)
    maximum_radius = max(max(anchors[index].radius for index in eligible), 1e-6)

    scores: dict[int, float] = {}
    for index in eligible:
        anchor = anchors[index]
        depth_score = anchor.hierarchy_depth / maximum_depth
        radius_score = 1.0 - min(anchor.radius / maximum_radius, 1.0)
        outward_score = radial[index] / maximum_radial
        scores[index] = (
            0.30 * depth_score
            + 0.25 * radius_score
            + 0.25 * anchor.branch_progress
            + 0.20 * outward_score
        )
    return scores


def _group_ordered_branch_indices(
    anchors: list[FoliageAnchor],
    eligible: list[int],
    *,
    reverse_progress: bool,
) -> dict[int, list[int]]:
    branches: dict[int, list[int]] = {}
    for index in eligible:
        branches.setdefault(anchors[index].branch_id, []).append(index)
    for indices in branches.values():
        indices.sort(
            key=lambda index: (
                -anchors[index].branch_progress
                if reverse_progress
                else anchors[index].branch_progress,
                index,
            )
        )
    return branches


def _is_spaced_from_selected(
    anchors: list[FoliageAnchor],
    candidate: int,
    selected: list[int],
    minimum_spacing: float,
) -> bool:
    if minimum_spacing <= 0.0:
        return True
    minimum_squared = minimum_spacing * minimum_spacing
    return all(
        _distance_squared(
            anchors[candidate].position, anchors[selected_index].position
        )
        + 1e-12
        >= minimum_squared
        for selected_index in selected
    )


def _select_spaced_branch_indices(
    anchors: list[FoliageAnchor],
    branches: dict[int, list[int]],
    branch_order: list[int],
    count: int,
    base_spacing: float,
    selected_prefix: list[int] | None = None,
) -> list[int]:
    """Select branch candidates in fixed spacing phases with per-branch cursors."""

    if count <= 0 or not branches:
        return []
    remaining = {branch_id: indices.copy() for branch_id, indices in branches.items()}
    selected = list(selected_prefix or [])
    prefix_length = len(selected)

    for phase_factor in _SPACING_PHASE_FACTORS:
        phase_spacing = base_spacing * phase_factor
        while len(selected) - prefix_length < count:
            added = False
            for branch_id in branch_order:
                candidates = remaining[branch_id]
                accepted_offset = next(
                    (
                        offset
                        for offset, candidate in enumerate(candidates)
                        if _is_spaced_from_selected(
                            anchors, candidate, selected, phase_spacing
                        )
                    ),
                    None,
                )
                if accepted_offset is None:
                    continue
                candidate = candidates[accepted_offset]
                # This list is the branch cursor. Once spacing makes us scan past
                # an anchor, consuming the whole prefix prevents a later tighter
                # phase from walking back toward the tip/junction.
                del candidates[: accepted_offset + 1]
                selected.append(candidate)
                added = True
                if len(selected) - prefix_length == count:
                    break
            if not added:
                break
        if len(selected) - prefix_length == count:
            break
    return selected[prefix_length:]


def _select_physical_branch_indices(
    anchors: list[FoliageAnchor],
    eligible: list[int],
    count: int,
    rng: random.Random,
    minimum_spacing: float,
    selected_prefix: list[int] | None = None,
) -> list[int]:
    """Consume retained secondary branches from connection to tip."""

    if count <= 0 or not eligible:
        return []
    branches = _group_ordered_branch_indices(
        anchors, eligible, reverse_progress=False
    )

    scores = _anchor_scores(anchors, eligible)
    branch_jitter = {
        branch_id: rng.random() * 1e-8 for branch_id in sorted(branches)
    }
    branch_order = sorted(
        branches,
        key=lambda branch_id: (
            max(scores[index] for index in branches[branch_id])
            + branch_jitter[branch_id]
        ),
        reverse=True,
    )

    selected = list(selected_prefix or [])
    prefix_length = len(selected)
    remaining = {branch_id: indices.copy() for branch_id, indices in branches.items()}
    if any(
        candidates
        and anchors[candidates[0]].branch_progress <= 1e-6
        for candidates in remaining.values()
    ):
        for branch_id in branch_order:
            candidates = remaining[branch_id]
            if not candidates or anchors[candidates[0]].branch_progress > 1e-6:
                continue
            selected.append(candidates.pop(0))
            if len(selected) - prefix_length == count:
                return selected[prefix_length:]

    selected.extend(_select_spaced_branch_indices(
        anchors,
        remaining,
        branch_order,
        count - (len(selected) - prefix_length),
        minimum_spacing,
        selected,
    ))
    return selected[prefix_length:]


def _select_missing_branch_indices(
    anchors: list[FoliageAnchor],
    eligible: list[int],
    count: int,
    rng: random.Random,
    minimum_spacing: float,
    selected_prefix: list[int] | None = None,
) -> list[int]:
    """Consume omitted secondary branches from connection to tip."""

    if count <= 0 or not eligible:
        return []
    branches = _group_ordered_branch_indices(
        anchors, eligible, reverse_progress=False
    )

    branch_order = sorted(branches)
    rng.shuffle(branch_order)
    selected = list(selected_prefix or [])
    prefix_length = len(selected)
    remaining = {branch_id: indices.copy() for branch_id, indices in branches.items()}
    if any(
        candidates
        and anchors[candidates[0]].branch_progress <= 1e-6
        for candidates in remaining.values()
    ):
        for branch_id in branch_order:
            candidates = remaining[branch_id]
            if not candidates or anchors[candidates[0]].branch_progress > 1e-6:
                continue
            selected.append(candidates.pop(0))
            if len(selected) - prefix_length == count:
                return selected[prefix_length:]

    selected.extend(_select_spaced_branch_indices(
        anchors,
        remaining,
        branch_order,
        count - (len(selected) - prefix_length),
        minimum_spacing,
        selected,
    ))
    return selected[prefix_length:]


def select_anchor_indices_with_branch_priority(
    anchors: list[FoliageAnchor],
    eligible: list[int],
    count: int,
    rng: random.Random,
    missing_branch_ids: frozenset[int],
    minimum_spacing: float = 0.0,
) -> list[int]:
    """Select primary connections, secondary connections, then outward anchors."""

    def partition(indices: list[int]) -> tuple[list[int], list[int]]:
        return (
            [
                index
                for index in indices
                if anchors[index].branch_id not in missing_branch_ids
            ],
            [
                index
                for index in indices
                if anchors[index].branch_id in missing_branch_ids
            ],
        )

    primary_connections = [
        index
        for index in eligible
        if anchors[index].hierarchy_depth == 1
        and anchors[index].branch_progress <= 1e-6
    ]
    secondary_connections = [
        index
        for index in eligible
        if anchors[index].hierarchy_depth >= 2
        and anchors[index].branch_progress <= 1e-6
    ]
    outward = [
        index for index in eligible if anchors[index].branch_progress > 1e-6
    ]
    selected: list[int] = []
    for candidates in (primary_connections, secondary_connections, outward):
        physical, missing = partition(candidates)
        for group, selector in (
            (physical, _select_physical_branch_indices),
            (missing, _select_missing_branch_indices),
        ):
            remaining = count - len(selected)
            if remaining <= 0:
                break
            take = min(remaining, len(group))
            if take:
                selected.extend(
                    selector(
                        anchors,
                        group,
                        take,
                        rng,
                        minimum_spacing,
                        selected,
                    )
                )
        if len(selected) == count:
            break

    if len(selected) < count:
        if not selected:
            raise ValueError("No eligible foliage anchors were available for selection")
        repeat_order = selected.copy()
        rng.shuffle(repeat_order)
        while len(selected) < count:
            selected.append(repeat_order[(len(selected) - len(repeat_order)) % len(repeat_order)])
    return selected


def _base_scale(anchors: list[FoliageAnchor], eligible: list[int]) -> float:
    positions = [anchors[index].position for index in eligible]
    extents = [
        max(position[axis] for position in positions)
        - min(position[axis] for position in positions)
        for axis in range(3)
    ]
    crown_width = max(extents[0], extents[1], extents[2] * 0.55, 1.0)
    reference_density = math.sqrt(DEFAULT_SCALE_REFERENCE_CLUSTERS) * 1.7
    return max(0.1, crown_width / reference_density)


def _stable_normal(
    direction: tuple[float, float, float], roll: float
) -> tuple[float, float, float]:
    reference = (0.0, 0.0, 1.0) if abs(direction[2]) < 0.92 else (0.0, 1.0, 0.0)
    normal = _normalize(_cross(direction, reference))
    return _normalize(_rotate_about_axis(normal, direction, roll))


def terminal_trunk_anchor_index(anchors: list[FoliageAnchor]) -> int:
    """Return the highest deterministic terminal anchor from the depth-zero trunk."""

    validated = [validate_anchor(anchor) for anchor in anchors]
    trunk_branches: dict[int, list[int]] = {}
    for index, anchor in enumerate(validated):
        if anchor.hierarchy_depth == 0:
            trunk_branches.setdefault(anchor.branch_id, []).append(index)
    if not trunk_branches:
        raise ValueError("Complete tree graph has no trunk anchors for Top Tip Pairs")

    terminals = [
        max(
            indices,
            key=lambda index: (validated[index].branch_progress, -index),
        )
        for _, indices in sorted(trunk_branches.items())
    ]
    return max(
        terminals,
        key=lambda index: (
            validated[index].position[2],
            validated[index].branch_progress,
            -validated[index].branch_id,
            -index,
        ),
    )


def build_card_layout(
    anchors: list[FoliageAnchor],
    cluster_count: int,
    scale_multiplier: float,
    seed: int,
    v_angle_degrees: float = DEFAULT_V_ANGLE_DEGREES,
    pair_rotation_radians: float = 0.0,
    template_slots: tuple[int, ...] = (1,),
    missing_branch_ids: frozenset[int] = frozenset(),
    branch_spacing: float = 1.0,
    template_footprint: float = 1.0,
    branch_card_length: float = 1.5,
    primary_card_length: float = 2.0,
    length_variation: float = 0.0,
    include_primary_connections: bool = False,
    top_tip_pairs: int = 0,
) -> list[CardPlacement]:
    """Return exactly two branch-aligned cards for every requested cluster."""

    if not anchors:
        raise ValueError("At least one foliage anchor is required")
    if cluster_count < 1:
        raise ValueError("Foliage cluster count must be at least one")
    if not math.isfinite(scale_multiplier) or scale_multiplier <= 0.0:
        raise ValueError("Card scale must be finite and greater than zero")
    if not math.isfinite(v_angle_degrees) or not 1.0 <= v_angle_degrees <= 179.0:
        raise ValueError("Card V angle must be between 1 and 179 degrees")
    if not math.isfinite(pair_rotation_radians):
        raise ValueError("Card pair rotation must be finite")
    if not math.isfinite(branch_spacing) or not 0.1 <= branch_spacing <= 3.0:
        raise ValueError("Branch Spacing must be between 0.1x and 3.0x")
    if not math.isfinite(template_footprint) or template_footprint <= 0.0:
        raise ValueError("Foliage template footprint must be finite and greater than zero")
    if not math.isfinite(branch_card_length) or not 0.5 <= branch_card_length <= 3.0:
        raise ValueError("Branch Card Length must be between 0.5x and 3.0x")
    if not math.isfinite(primary_card_length) or not 0.5 <= primary_card_length <= 4.0:
        raise ValueError("Primary Card Length must be between 0.5x and 4.0x")
    if not math.isfinite(length_variation) or not 0.0 <= length_variation <= 0.5:
        raise ValueError("Length Variation must be between 0% and 50%")
    if not isinstance(top_tip_pairs, int) or not 0 <= top_tip_pairs <= 2:
        raise ValueError("Top Tip Pairs must be an integer between 0 and 2")

    validated = [validate_anchor(anchor) for anchor in anchors]
    eligible = foliage_branch_candidate_indices(
        validated,
        missing_branch_ids,
        include_primary_connections=include_primary_connections,
    )
    base_scale = _base_scale(validated, eligible) * scale_multiplier
    minimum_spacing = base_scale * template_footprint * branch_spacing
    selection_rng = random.Random(int(seed) ^ 0x4C957F2D)
    reserved_tip_count = min(top_tip_pairs, cluster_count)
    terminal_index = (
        terminal_trunk_anchor_index(validated) if reserved_tip_count else None
    )
    selected = [terminal_index] * reserved_tip_count
    remaining_count = cluster_count - reserved_tip_count
    if remaining_count:
        selected.extend(
            select_anchor_indices_with_branch_priority(
                validated,
                eligible,
                remaining_count,
                selection_rng,
                missing_branch_ids,
                minimum_spacing,
            )
        )
    assigned_slots = _template_slots_for_clusters(cluster_count, template_slots, seed)
    half_angle = math.radians(v_angle_degrees) * 0.5
    appearance_rng = random.Random(int(seed) ^ 0xA341316C)
    length_rng = random.Random(int(seed) ^ 0x27D4EB2F)

    placements: list[CardPlacement] = []
    repetitions: dict[int, int] = {}
    for cluster_index, anchor_index in enumerate(selected):
        if anchor_index is None:  # Narrow the reserved-tip Optional for type checkers.
            raise ValueError("Top Tip Pairs could not resolve a terminal trunk anchor")
        anchor = validated[anchor_index]
        direction = _normalize(anchor.direction)
        is_top_tip = cluster_index < reserved_tip_count
        if is_top_tip:
            tip_roll = cluster_index * math.pi * 0.5
            base_normal = _stable_normal(
                direction, pair_rotation_radians + tip_roll
            )
            normal = base_normal
            position = anchor.position
        else:
            base_normal = _stable_normal(
                direction, appearance_rng.uniform(-math.pi, math.pi)
            )
            normal = _normalize(
                _rotate_about_axis(base_normal, direction, pair_rotation_radians)
            )
            repetition = repetitions.get(anchor_index, 0)
            repetitions[anchor_index] = repetition + 1
            jitter_scale = base_scale * 0.18 * repetition
            jitter_angle = appearance_rng.uniform(-math.pi, math.pi)
            side = _normalize(_cross(base_normal, direction))
            position = tuple(
                anchor.position[axis]
                + side[axis] * math.cos(jitter_angle) * jitter_scale
                + base_normal[axis] * math.sin(jitter_angle) * jitter_scale
                for axis in range(3)
            )
        varied_scale = base_scale * appearance_rng.uniform(0.88, 1.12)
        base_length = (
            primary_card_length
            if anchor.hierarchy_depth == 1
            else branch_card_length
        )
        effective_length = base_length * length_rng.uniform(
            1.0 - length_variation, 1.0 + length_variation
        )

        for card_index, angle in enumerate((-half_angle, half_angle)):
            card_normal = _normalize(_rotate_about_axis(normal, direction, angle))
            placements.append(
                CardPlacement(
                    cluster_index=cluster_index,
                    card_index=card_index,
                    anchor_index=anchor_index,
                    position=position,
                    direction=direction,
                    normal=card_normal,
                    scale=varied_scale,
                    length_scale=effective_length,
                    template_slot=assigned_slots[cluster_index],
                    is_top_tip=is_top_tip,
                )
            )
    return placements
