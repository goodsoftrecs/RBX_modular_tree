"""Pure deterministic layout helpers for low-poly canopy lobes."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


ROUND_TEMPLATE = "Canopy_Round"
WIDE_TEMPLATE = "Canopy_Wide"
TIP_TEMPLATE = "Canopy_Tip"


@dataclass(frozen=True)
class Anchor:
    """A retained branch endpoint that may receive a canopy lobe."""

    position: tuple[float, float, float]
    direction: tuple[float, float, float]
    depth: int


@dataclass(frozen=True)
class LobePlacement:
    """Resolved placement for one reusable canopy template."""

    anchor_index: int
    template_name: str
    position: tuple[float, float, float]
    rotation: tuple[float, float, float]
    scale: float


def _distance_squared(
    first: tuple[float, float, float], second: tuple[float, float, float]
) -> float:
    return sum((a - b) ** 2 for a, b in zip(first, second, strict=True))


def _select_anchor_indices(anchors: list[Anchor], count: int, rng: random.Random) -> list[int]:
    """Choose spatially distributed real anchors, then deterministically repeat if necessary."""

    unique_target = min(count, len(anchors))
    tie_breakers = [rng.random() * 1e-9 for _ in anchors]
    selected = [rng.randrange(len(anchors))]

    while len(selected) < unique_target:
        remaining = [index for index in range(len(anchors)) if index not in selected]
        next_index = max(
            remaining,
            key=lambda index: min(
                _distance_squared(anchors[index].position, anchors[chosen].position)
                for chosen in selected
            )
            + tie_breakers[index],
        )
        selected.append(next_index)

    if count > len(selected):
        repeat_order = selected.copy()
        rng.shuffle(repeat_order)
        while len(selected) < count:
            selected.append(repeat_order[(len(selected) - unique_target) % len(repeat_order)])

    return selected


def _classify_template(
    anchor: Anchor,
    center: tuple[float, float],
    max_radius: float,
    min_z: float,
    height: float,
) -> str:
    x, y, z = anchor.position
    dx, dy, dz = anchor.direction
    z_normalized = (z - min_z) / max(height, 1e-6)
    radial = math.hypot(x - center[0], y - center[1]) / max(max_radius, 1e-6)
    direction_length = max(math.sqrt(dx * dx + dy * dy + dz * dz), 1e-6)
    horizontal_direction = math.hypot(dx, dy) / direction_length

    if z_normalized >= 0.72:
        return TIP_TEMPLATE
    if horizontal_direction >= 0.7:
        return WIDE_TEMPLATE
    if radial >= 0.82:
        return TIP_TEMPLATE
    return ROUND_TEMPLATE


def _base_scale(anchors: list[Anchor], count: int) -> float:
    xs = [anchor.position[0] for anchor in anchors]
    ys = [anchor.position[1] for anchor in anchors]
    zs = [anchor.position[2] for anchor in anchors]
    crown_width = max(max(xs) - min(xs), max(ys) - min(ys))
    if crown_width <= 1e-6:
        crown_width = max(max(zs) - min(zs), 1.0) * 0.5
    return max(0.1, crown_width / (2.0 * math.sqrt(count)))


def build_lobe_layout(
    anchors: list[Anchor],
    count: int,
    scale_multiplier: float,
    seed: int,
) -> list[LobePlacement]:
    """Build an exact, deterministic canopy layout from retained branch endpoints."""

    if not anchors:
        raise ValueError("At least one canopy anchor is required")
    if count < 1:
        raise ValueError("Lobe count must be at least one")
    if scale_multiplier <= 0:
        raise ValueError("Lobe scale must be greater than zero")

    rng = random.Random(int(seed))
    selected_indices = _select_anchor_indices(anchors, count, rng)

    xs = [anchor.position[0] for anchor in anchors]
    ys = [anchor.position[1] for anchor in anchors]
    zs = [anchor.position[2] for anchor in anchors]
    center = ((min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5)
    max_radius = max(math.hypot(x - center[0], y - center[1]) for x, y in zip(xs, ys, strict=True))
    min_z = min(zs)
    height = max(zs) - min_z
    base_scale = _base_scale(anchors, count)

    repetitions: dict[int, int] = {}
    placements: list[LobePlacement] = []
    for anchor_index in selected_indices:
        anchor = anchors[anchor_index]
        template_name = _classify_template(anchor, center, max_radius, min_z, height)
        dx, dy, _ = anchor.direction
        branch_yaw = math.atan2(dy, dx) if abs(dx) + abs(dy) > 1e-6 else 0.0
        yaw = branch_yaw if template_name == WIDE_TEMPLATE else rng.uniform(-math.pi, math.pi)
        rotation = (
            rng.uniform(-0.12, 0.12),
            rng.uniform(-0.12, 0.12),
            yaw + rng.uniform(-0.2, 0.2),
        )

        repetition = repetitions.get(anchor_index, 0)
        repetitions[anchor_index] = repetition + 1
        jitter_radius = base_scale * 0.35 * repetition
        jitter_angle = rng.uniform(-math.pi, math.pi)
        position = (
            anchor.position[0] + math.cos(jitter_angle) * jitter_radius,
            anchor.position[1] + math.sin(jitter_angle) * jitter_radius,
            anchor.position[2] + rng.uniform(-0.08, 0.08) * base_scale,
        )
        varied_scale = base_scale * rng.uniform(0.9, 1.1)
        placements.append(
            LobePlacement(
                anchor_index=anchor_index,
                template_name=template_name,
                position=position,
                rotation=rotation,
                scale=varied_scale * scale_multiplier,
            )
        )

    return placements

