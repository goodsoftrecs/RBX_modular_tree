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
    template_slot: int = 1


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
) -> tuple[dict[int, float], float]:
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
    crown_extent = max(
        math.sqrt(_distance_squared(first, second))
        for first in positions
        for second in positions
    )
    return scores, max(crown_extent, 1e-6)


def _select_anchor_indices(
    anchors: list[FoliageAnchor], eligible: list[int], count: int, rng: random.Random
) -> list[int]:
    scores, crown_extent = _anchor_scores(anchors, eligible)
    jitter = {index: rng.random() * 1e-8 for index in eligible}
    selected = [max(eligible, key=lambda index: scores[index] + jitter[index])]
    unique_target = min(count, len(eligible))

    while len(selected) < unique_target:
        remaining = [index for index in eligible if index not in selected]
        selected.append(
            max(
                remaining,
                key=lambda index: (
                    0.65
                    * min(
                        math.sqrt(
                            _distance_squared(
                                anchors[index].position, anchors[chosen].position
                            )
                        )
                        / crown_extent
                        for chosen in selected
                    )
                    + 0.35 * scores[index]
                    + jitter[index]
                ),
            )
        )

    if len(selected) < count:
        repeat_order = selected.copy()
        rng.shuffle(repeat_order)
        while len(selected) < count:
            selected.append(repeat_order[(len(selected) - unique_target) % len(repeat_order)])
    return selected


def _select_missing_branch_indices(
    anchors: list[FoliageAnchor],
    eligible: list[int],
    count: int,
    rng: random.Random,
) -> list[int]:
    """Consume missing branches round-robin from attachment-side progress outward."""

    if count <= 0 or not eligible:
        return []
    branches: dict[int, list[int]] = {}
    for index in eligible:
        branches.setdefault(anchors[index].branch_id, []).append(index)
    for indices in branches.values():
        indices.sort(key=lambda index: (anchors[index].branch_progress, index))

    branch_order = sorted(branches)
    rng.shuffle(branch_order)
    selected: list[int] = []
    layer = 0
    while len(selected) < count:
        added = False
        for branch_id in branch_order:
            indices = branches[branch_id]
            if layer < len(indices):
                selected.append(indices[layer])
                added = True
                if len(selected) == count:
                    break
        if not added:
            break
        layer += 1
    return selected


def select_anchor_indices_with_branch_priority(
    anchors: list[FoliageAnchor],
    eligible: list[int],
    count: int,
    rng: random.Random,
    missing_branch_ids: frozenset[int],
) -> list[int]:
    """Select physical anchors first, then missing branches connection-outward."""

    physical = [
        index for index in eligible if anchors[index].branch_id not in missing_branch_ids
    ]
    missing = [
        index for index in eligible if anchors[index].branch_id in missing_branch_ids
    ]

    selected: list[int] = []
    physical_count = min(count, len(physical))
    if physical_count:
        selected.extend(_select_anchor_indices(anchors, physical, physical_count, rng))

    remaining = count - len(selected)
    if remaining and missing:
        selected.extend(
            _select_missing_branch_indices(anchors, missing, remaining, rng)
        )

    if len(selected) < count:
        if not selected:
            raise ValueError("No eligible foliage anchors were available for selection")
        repeat_order = selected.copy()
        rng.shuffle(repeat_order)
        while len(selected) < count:
            selected.append(repeat_order[(len(selected) - len(repeat_order)) % len(repeat_order)])
    return selected


def _base_scale(anchors: list[FoliageAnchor], eligible: list[int], count: int) -> float:
    positions = [anchors[index].position for index in eligible]
    extents = [
        max(position[axis] for position in positions)
        - min(position[axis] for position in positions)
        for axis in range(3)
    ]
    crown_width = max(extents[0], extents[1], extents[2] * 0.55, 1.0)
    return max(0.1, crown_width / max(math.sqrt(count) * 1.7, 1.0))


def _stable_normal(
    direction: tuple[float, float, float], roll: float
) -> tuple[float, float, float]:
    reference = (0.0, 0.0, 1.0) if abs(direction[2]) < 0.92 else (0.0, 1.0, 0.0)
    normal = _normalize(_cross(direction, reference))
    return _normalize(_rotate_about_axis(normal, direction, roll))


def build_card_layout(
    anchors: list[FoliageAnchor],
    cluster_count: int,
    scale_multiplier: float,
    seed: int,
    v_angle_degrees: float = DEFAULT_V_ANGLE_DEGREES,
    pair_rotation_radians: float = 0.0,
    template_slots: tuple[int, ...] = (1,),
    missing_branch_ids: frozenset[int] = frozenset(),
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

    validated = [validate_anchor(anchor) for anchor in anchors]
    eligible = eligible_anchor_indices(validated, missing_branch_ids)
    rng = random.Random(int(seed))
    selected = select_anchor_indices_with_branch_priority(
        validated,
        eligible,
        cluster_count,
        rng,
        missing_branch_ids,
    )
    assigned_slots = _template_slots_for_clusters(cluster_count, template_slots, seed)
    base_scale = _base_scale(validated, eligible, cluster_count) * scale_multiplier
    half_angle = math.radians(v_angle_degrees) * 0.5

    placements: list[CardPlacement] = []
    repetitions: dict[int, int] = {}
    for cluster_index, anchor_index in enumerate(selected):
        anchor = validated[anchor_index]
        direction = _normalize(anchor.direction)
        base_normal = _stable_normal(direction, rng.uniform(-math.pi, math.pi))
        normal = _normalize(
            _rotate_about_axis(base_normal, direction, pair_rotation_radians)
        )
        repetition = repetitions.get(anchor_index, 0)
        repetitions[anchor_index] = repetition + 1
        jitter_scale = base_scale * 0.18 * repetition
        jitter_angle = rng.uniform(-math.pi, math.pi)
        side = _normalize(_cross(base_normal, direction))
        position = tuple(
            anchor.position[axis]
            + side[axis] * math.cos(jitter_angle) * jitter_scale
            + base_normal[axis] * math.sin(jitter_angle) * jitter_scale
            for axis in range(3)
        )
        varied_scale = base_scale * rng.uniform(0.88, 1.12)

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
                    template_slot=assigned_slots[cluster_index],
                )
            )
    return placements
