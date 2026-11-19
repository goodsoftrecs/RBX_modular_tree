"""Tree generation presets for quick tree creation.

This module defines preset configurations for different tree types.
Each preset specifies branch function parameters that produce a
characteristic tree shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from random import randint
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

# Parameters that require PropertyWrapper (ConstantProperty) instead of raw values
PROPERTY_WRAPPER_PARAMS = {"length", "start_radius", "randomness", "start_angle"}

# Mapping from preset parameter names to nested C++ struct paths on BranchFunction.
# Parameters not in this map are set directly on BranchFunction.
_NESTED_PROPERTY_MAP = {
    "start": ("distribution", "start"),
    "end": ("distribution", "end"),
    "branches_density": ("distribution", "density"),
    "phillotaxis": ("distribution", "phillotaxis"),
    "gravity_strength": ("gravity", "strength"),
    "stiffness": ("gravity", "stiffness"),
    "up_attraction": ("gravity", "up_attraction"),
    "split_proba": ("split", "probability"),
    "split_radius": ("split", "radius"),
    "split_angle": ("split", "angle"),
    "crown_shape": ("crown", "shape"),
    "crown_base_size": ("crown", "base_size"),
    "crown_height": ("crown", "height"),
    "crown_angle_variation": ("crown", "angle_variation"),
}


@dataclass
class TreePreset:
    """Configuration for a tree generation preset."""

    name: str
    label: str
    description: str
    branches: dict[str, Any] = field(default_factory=dict)
    trunk: dict[str, Any] = field(default_factory=dict)
    growth: dict[str, Any] = field(default_factory=dict)
    sub_branches: dict[str, Any] = field(default_factory=dict)
    leaf_params: dict[str, Any] = field(default_factory=dict)

    def to_enum_item(self) -> tuple[str, str, str]:
        """Convert to Blender EnumProperty item tuple."""
        return (self.name, self.label, self.description)


# Default trunk parameters shared across presets
_DEFAULT_TRUNK_PARAMS = {
    "length": 14,
    "start_radius": 0.3,
    "end_radius": 0.05,
    "shape": 0.7,
    "up_attraction": 0.6,
    "resolution": 3,
    "randomness": 1,
}

# Default branch parameters shared across presets
_DEFAULT_BRANCH_PARAMS = {
    "start": 0.1,
    "end": 0.95,
    "branches_density": 2.0,
    "resolution": 3,
    "split_proba": 0.5,
    "break_chance": 0.02,
    "start_radius": 0.4,
    "start_angle": 45,
    "gravity_strength": 10,
    "randomness": 0.5,
}


TREE_PRESETS: dict[str, TreePreset] = {
    "OAK": TreePreset(
        name="OAK",
        label="Oak",
        description="Broad spreading tree with thick trunk",
        trunk={
            "length": 7,  # Shorter trunk - oaks branch low
            "start_radius": 0.5,  # Thicker base
            "end_radius": 0.15,  # Less taper - branches into major limbs
            "shape": 0.5,  # More gradual taper
            "up_attraction": 0.5,  # Straighter trunk
        },
        branches={
            "start": 0.15,  # Branches start slightly up the trunk
            "length": 8,  # Shorter branches that split more
            "branches_density": 1.8,  # Many branches to fill crown
            "start_angle": 55,  # Less horizontal, more room to grow up
            "gravity_strength": 6,  # Much less droop - branches hold up
            "up_attraction": 0.45,  # More upward growth for dome shape
            "flatness": 0.35,  # Slightly less flat
            "stiffness": 0.2,  # Stiffer branches resist gravity
            "split_proba": 0.65,  # More splitting for denser crown
        },
        sub_branches={
            "start": 0.45,
            "end": 0.95,
            "length": 2.2,
            "branches_density": 0.7,
            "start_angle": 45,
            "gravity_strength": 8,
            "stiffness": 0.25,
            "up_attraction": 0.3,
            "flatness": 0.4,
            "split_proba": 0.15,
            "start_radius": 0.45,
            "randomness": 0.45,
        },
    ),
    "BIRCH": TreePreset(
        name="BIRCH",
        label="Birch",
        description="Slender trunk with a light, upright crown",
        trunk={
            "length": 13,
            "start_radius": 0.24,
            "end_radius": 0.045,
            "shape": 0.85,
            "up_attraction": 0.75,
            "randomness": 0.35,
        },
        branches={
            "start": 0.32,
            "length": 4.2,
            "branches_density": 1.15,
            "start_angle": 42,
            "gravity_strength": 7,
            "up_attraction": 0.5,
            "flatness": 0.3,
            "stiffness": 0.25,
            "split_proba": 0.35,
            "start_radius": 0.32,
            "randomness": 0.55,
            "crown_shape": "TendFlame",
        },
        sub_branches={
            "start": 0.35,
            "end": 0.95,
            "length": 1.8,
            "branches_density": 0.8,
            "start_angle": 42,
            "gravity_strength": 8,
            "stiffness": 0.2,
            "up_attraction": 0.35,
            "flatness": 0.4,
            "split_proba": 0.1,
            "start_radius": 0.35,
            "randomness": 0.55,
        },
    ),
    "PINE": TreePreset(
        name="PINE",
        label="Pine",
        description="Tall conifer with horizontal tiered branches",
        trunk={
            "length": 14,
            "start_radius": 0.3,
            "end_radius": 0.05,
            "shape": 1.0,
            "up_attraction": 0.6,
            "randomness": 0.2,
        },
        branches={
            "start": 0.2,
            "length": 7,
            "branches_density": 2.5,
            "start_angle": 60,
            "randomness": 0.5,
            "flatness": 0.5,
            "up_attraction": 0.0,
            "gravity_strength": 10,
            "stiffness": 0.1,
            "split_proba": 0.5,
            "split_radius": 0.8,
            "split_angle": 35,
            "phillotaxis": 137.5,
            "break_chance": 0.01,
            "start_radius": 0.4,
            "crown_shape": "Conical",
        },
        sub_branches={
            "start": 0.1,
            "end": 0.95,
            "length": 2,
            "branches_density": 1.0,
            "start_angle": 45,
            "randomness": 0.5,
            "flatness": 1.0,
            "up_attraction": 0.0,
            "gravity_strength": 14,
            "stiffness": 0.1,
            "split_proba": 0.5,
            "split_radius": 0.8,
            "split_angle": 35,
            "phillotaxis": 137.5,
            "break_chance": 0.02,
            "resolution": 3,
            "start_radius": 0.4,
        },
        leaf_params={
            "density": 350.0,
            "scale": 1.0,
            "max_radius": 0.03,
        },
    ),
    "CEDAR": TreePreset(
        name="CEDAR",
        label="Cedar",
        description="Layered conifer with broad, gently drooping limbs",
        trunk={
            "length": 11,
            "start_radius": 0.38,
            "end_radius": 0.08,
            "shape": 0.8,
            "up_attraction": 0.7,
            "randomness": 0.25,
        },
        branches={
            "start": 0.18,
            "length": 7.5,
            "branches_density": 1.35,
            "start_angle": 72,
            "gravity_strength": 18,
            "up_attraction": -0.05,
            "flatness": 0.65,
            "stiffness": 0.18,
            "split_proba": 0.35,
            "start_radius": 0.45,
            "randomness": 0.4,
            "crown_shape": "Conical",
        },
        sub_branches={
            "start": 0.2,
            "end": 0.95,
            "length": 2.5,
            "branches_density": 1.6,
            "start_angle": 55,
            "gravity_strength": 24,
            "stiffness": 0.12,
            "up_attraction": -0.15,
            "flatness": 0.8,
            "split_proba": 0.12,
            "start_radius": 0.35,
            "randomness": 0.45,
        },
    ),
    "WALNUT": TreePreset(
        name="WALNUT",
        label="Walnut",
        description="Strong open branching under a rounded crown",
        trunk={
            "length": 8,
            "start_radius": 0.48,
            "end_radius": 0.14,
            "shape": 0.55,
            "up_attraction": 0.55,
            "randomness": 0.55,
        },
        branches={
            "start": 0.25,
            "length": 7,
            "branches_density": 1.35,
            "start_angle": 52,
            "gravity_strength": 7,
            "up_attraction": 0.4,
            "flatness": 0.35,
            "stiffness": 0.3,
            "split_proba": 0.55,
            "start_radius": 0.55,
            "randomness": 0.65,
            "crown_shape": "Spherical",
        },
        sub_branches={
            "start": 0.4,
            "end": 0.95,
            "length": 2.4,
            "branches_density": 0.8,
            "start_angle": 48,
            "gravity_strength": 8,
            "stiffness": 0.22,
            "up_attraction": 0.3,
            "flatness": 0.45,
            "split_proba": 0.15,
            "start_radius": 0.4,
            "randomness": 0.6,
        },
    ),
    "SEQUOIA": TreePreset(
        name="SEQUOIA",
        label="Sequoia",
        description="Very tall tapered trunk with compact conifer branching",
        trunk={
            "length": 22,
            "start_radius": 0.65,
            "end_radius": 0.08,
            "shape": 0.95,
            "up_attraction": 0.85,
            "randomness": 0.18,
        },
        branches={
            "start": 0.24,
            "length": 5.5,
            "branches_density": 1.45,
            "start_angle": 78,
            "gravity_strength": 10,
            "up_attraction": 0.15,
            "flatness": 0.55,
            "stiffness": 0.24,
            "split_proba": 0.3,
            "start_radius": 0.38,
            "randomness": 0.35,
            "crown_shape": "Conical",
        },
        sub_branches={
            "start": 0.25,
            "end": 0.95,
            "length": 1.8,
            "branches_density": 1.0,
            "start_angle": 50,
            "gravity_strength": 12,
            "stiffness": 0.18,
            "up_attraction": 0.05,
            "flatness": 0.7,
            "split_proba": 0.08,
            "start_radius": 0.3,
            "randomness": 0.4,
        },
    ),
    "HEMLOCK": TreePreset(
        name="HEMLOCK",
        label="Hemlock",
        description="Narrow conifer with soft, drooping branch tips",
        trunk={
            "length": 13,
            "start_radius": 0.32,
            "end_radius": 0.055,
            "shape": 0.9,
            "up_attraction": 0.72,
            "randomness": 0.3,
        },
        branches={
            "start": 0.2,
            "length": 6,
            "branches_density": 1.55,
            "start_angle": 74,
            "gravity_strength": 22,
            "up_attraction": -0.15,
            "flatness": 0.6,
            "stiffness": 0.12,
            "split_proba": 0.35,
            "start_radius": 0.38,
            "randomness": 0.55,
            "crown_shape": "Conical",
        },
        sub_branches={
            "start": 0.25,
            "end": 0.95,
            "length": 2.2,
            "branches_density": 1.35,
            "start_angle": 52,
            "gravity_strength": 30,
            "stiffness": 0.08,
            "up_attraction": -0.35,
            "flatness": 0.75,
            "split_proba": 0.1,
            "start_radius": 0.32,
            "randomness": 0.55,
        },
    ),
    "TEAK": TreePreset(
        name="TEAK",
        label="Teak",
        description="Tall clear trunk supporting a high spreading crown",
        trunk={
            "length": 11,
            "start_radius": 0.45,
            "end_radius": 0.1,
            "shape": 0.68,
            "up_attraction": 0.7,
            "randomness": 0.35,
        },
        branches={
            "start": 0.43,
            "length": 6.5,
            "branches_density": 1.2,
            "start_angle": 50,
            "gravity_strength": 8,
            "up_attraction": 0.45,
            "flatness": 0.3,
            "stiffness": 0.28,
            "split_proba": 0.5,
            "start_radius": 0.48,
            "randomness": 0.5,
            "crown_shape": "Hemispherical",
        },
        sub_branches={
            "start": 0.4,
            "end": 0.95,
            "length": 2.5,
            "branches_density": 0.8,
            "start_angle": 45,
            "gravity_strength": 9,
            "stiffness": 0.2,
            "up_attraction": 0.35,
            "flatness": 0.4,
            "split_proba": 0.15,
            "start_radius": 0.38,
            "randomness": 0.55,
        },
    ),
    "DEAD_SNAG": TreePreset(
        name="DEAD_SNAG",
        label="Dead / Snag",
        description="Irregular standing deadwood with sparse broken limbs",
        trunk={
            "length": 10,
            "start_radius": 0.42,
            "end_radius": 0.12,
            "shape": 0.45,
            "up_attraction": 0.45,
            "randomness": 1.4,
        },
        branches={
            "start": 0.18,
            "end": 0.78,
            "length": 4.5,
            "branches_density": 0.35,
            "start_angle": 58,
            "gravity_strength": 5,
            "up_attraction": 0.1,
            "flatness": 0.25,
            "stiffness": 0.35,
            "split_proba": 0.12,
            "break_chance": 0.35,
            "start_radius": 0.42,
            "randomness": 1.2,
        },
    ),
    "RANDOM": TreePreset(
        name="RANDOM",
        label="Random",
        description="Random tree with varied parameters",
    ),
}


def get_preset_items() -> list[tuple[str, str, str]]:
    """Get preset enum items for Blender EnumProperty."""
    return [preset.to_enum_item() for preset in TREE_PRESETS.values()]


def _generate_random_params() -> dict[str, Any]:
    """Generate randomized branch parameters."""
    return {
        "length": randint(5, 15),
        "branches_density": 0.4 + (randint(0, 8) / 10),  # 0.4 to 1.2
        "start_angle": randint(30, 80),
        "gravity_strength": randint(5, 20),
        "up_attraction": 0.1 + (randint(0, 5) / 10),
        "flatness": randint(1, 5) / 10,
        "stiffness": 0.05 + (randint(0, 3) / 10),
    }


def _wrap_property_value(key: str, value):
    """Wrap value in PropertyWrapper(ConstantProperty) if the parameter requires it."""
    if key == "crown_shape":
        from ..m_tree_wrapper import lazy_m_tree as m_tree

        return getattr(m_tree.CrownShape, value)
    if key in PROPERTY_WRAPPER_PARAMS:
        from ..m_tree_wrapper import lazy_m_tree as m_tree

        constant = m_tree.ConstantProperty(float(value))
        return m_tree.PropertyWrapper(constant)
    return value


def _set_branch_param(branches, key: str, value) -> None:
    """Set a parameter on a BranchFunction, handling nested struct properties."""
    wrapped = _wrap_property_value(key, value)
    if key in _NESTED_PROPERTY_MAP:
        struct_name, field_name = _NESTED_PROPERTY_MAP[key]
        struct = getattr(branches, struct_name)
        setattr(struct, field_name, wrapped)
    else:
        setattr(branches, key, wrapped)


def _apply_branch_overrides(
    params: dict[str, Any],
    *,
    overall_size: float = 1.0,
    branch_length: float = 1.0,
    branch_density: float = 1.0,
    branch_spread: float = 1.0,
    branch_droop: float = 1.0,
    randomness: float = 1.0,
) -> dict[str, Any]:
    """Return branch parameters with conservative focused overrides applied."""

    resolved = dict(params)
    resolved["length"] = resolved["length"] * overall_size * branch_length
    resolved["branches_density"] = resolved["branches_density"] * branch_density
    resolved["start_angle"] = resolved.get("start_angle", 45) * branch_spread
    resolved["gravity_strength"] = resolved.get("gravity_strength", 10) * branch_droop
    resolved["randomness"] = resolved.get("randomness", 0.5) * randomness
    return resolved


def apply_preset(
    branches,
    preset_name: str,
    *,
    overall_size: float = 1.0,
    branch_length: float = 1.0,
    branch_density: float = 1.0,
    branch_spread: float = 1.0,
    branch_droop: float = 1.0,
    randomness: float = 1.0,
) -> None:
    """Apply a preset's parameters to a BranchFunction instance.

    Args:
        branches: A BranchFunction instance to configure.
        preset_name: Key from TREE_PRESETS or 'RANDOM' for randomized params.
    """
    params = dict(_DEFAULT_BRANCH_PARAMS)
    if preset_name == "RANDOM":
        params.update(_generate_random_params())
    else:
        preset = TREE_PRESETS.get(preset_name)
        if preset:
            params.update(preset.branches)

    params = _apply_branch_overrides(
        params,
        overall_size=overall_size,
        branch_length=branch_length,
        branch_density=branch_density,
        branch_spread=branch_spread,
        branch_droop=branch_droop,
        randomness=randomness,
    )

    for key, value in params.items():
        _set_branch_param(branches, key, value)


def apply_trunk_preset(
    trunk,
    preset_name: str,
    *,
    overall_size: float = 1.0,
    trunk_thickness: float = 1.0,
    randomness: float = 1.0,
) -> None:
    """Apply a preset's trunk parameters to a TrunkFunction instance.

    Args:
        trunk: A TrunkFunction instance to configure.
        preset_name: Key from TREE_PRESETS or 'RANDOM' for default params.
    """
    params = dict(_DEFAULT_TRUNK_PARAMS)
    if preset_name != "RANDOM":
        preset = TREE_PRESETS.get(preset_name)
        if preset and preset.trunk:
            params.update(preset.trunk)

    params["length"] *= overall_size
    params["start_radius"] *= overall_size * trunk_thickness
    params["end_radius"] *= overall_size * trunk_thickness
    params["randomness"] *= randomness

    for key, value in params.items():
        setattr(trunk, key, value)


def apply_sub_branch_preset(
    branches,
    preset_name: str,
    *,
    overall_size: float = 1.0,
    branch_length: float = 1.0,
    branch_density: float = 1.0,
    branch_spread: float = 1.0,
    branch_droop: float = 1.0,
    randomness: float = 1.0,
) -> None:
    """Apply a preset's sub_branches parameters to a BranchFunction instance.

    Args:
        branches: A BranchFunction instance to configure.
        preset_name: Key from TREE_PRESETS.
    """
    params = dict(_DEFAULT_BRANCH_PARAMS)
    preset = TREE_PRESETS.get(preset_name)
    if preset and preset.sub_branches:
        params.update(preset.sub_branches)

    params = _apply_branch_overrides(
        params,
        overall_size=overall_size,
        branch_length=branch_length,
        branch_density=branch_density,
        branch_spread=branch_spread,
        branch_droop=branch_droop,
        randomness=randomness,
    )

    for key, value in params.items():
        _set_branch_param(branches, key, value)


# Growth function presets
GROWTH_PRESETS: dict[str, dict] = {
    "STRUCTURED": {
        "iterations": 6,
        "apical_dominance": 0.85,
        "split_threshold": 0.8,
        "grow_threshold": 0.4,
        "gravitropism": 0.15,
        "randomness": 0.05,
    },
    "SPREADING": {
        "iterations": 5,
        "apical_dominance": 0.5,
        "split_threshold": 0.6,
        "grow_threshold": 0.3,
        "gravity_strength": 1.5,
    },
    "WEEPING": {
        "iterations": 7,
        "apical_dominance": 0.6,
        "gravitropism": -0.1,
        "gravity_strength": 3.0,
        "branch_length": 1.5,
        "randomness": 0.15,
    },
    "GNARLED": {
        "iterations": 8,
        "apical_dominance": 0.4,
        "split_threshold": 0.5,
        "randomness": 0.3,
        "gravity_strength": 2.0,
    },
}


def get_growth_preset_items() -> list[tuple[str, str, str]]:
    """Get growth preset enum items for Blender EnumProperty."""
    return [
        ("STRUCTURED", "Structured", "Orderly growth with strong apical dominance"),
        ("SPREADING", "Spreading", "Wide, spreading canopy with many branches"),
        ("WEEPING", "Weeping", "Drooping branches like a willow"),
        ("GNARLED", "Gnarled", "Twisted, organic growth pattern"),
    ]


def apply_growth_preset(growth_func, preset_name: str) -> None:
    """Apply a growth preset's parameters to a GrowthFunction instance.

    Args:
        growth_func: A GrowthFunction instance to configure.
        preset_name: Key from GROWTH_PRESETS.
    """
    preset = GROWTH_PRESETS.get(preset_name, {})
    for key, value in preset.items():
        if hasattr(growth_func, key):
            setattr(growth_func, key, value)
