"""Shared wood mesher profiles for authoring and game-ready output."""

from __future__ import annotations

from typing import NamedTuple


class WoodMesherSettings(NamedTuple):
    """Resolved settings passed to MTree's manifold wood mesher."""

    radial_resolution: int
    smooth_iterations: int
    longitudinal_stride: int


AUTHORING = "AUTHORING"
ROBLOX_GAME = "ROBLOX_GAME"

WOOD_OUTPUT_PROFILE_ITEMS = (
    (
        AUTHORING,
        "Authoring (Original)",
        "Use the editable radial resolution and smoothness settings",
    ),
    (
        ROBLOX_GAME,
        "Roblox Game (Low Detail)",
        "Generate lower-topology wood using 8-sided rings and one smoothing pass",
    ),
)

ROBLOX_GAME_SETTINGS = WoodMesherSettings(
    radial_resolution=8,
    smooth_iterations=1,
    longitudinal_stride=4,
)


def resolve_wood_mesher_settings(
    profile: str,
    authoring_radial_resolution: int,
    authoring_smooth_iterations: int,
) -> WoodMesherSettings:
    """Resolve a profile without changing the original authoring controls."""

    if profile == ROBLOX_GAME:
        return ROBLOX_GAME_SETTINGS

    return WoodMesherSettings(
        radial_resolution=max(3, int(authoring_radial_resolution)),
        smooth_iterations=max(0, int(authoring_smooth_iterations)),
        longitudinal_stride=1,
    )
