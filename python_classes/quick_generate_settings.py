"""Persistent scene settings for the sidebar quick tree generator."""

from __future__ import annotations

import bpy
from bpy.utils import register_class, unregister_class

from .game_output_profiles import ROBLOX_GAME_BUDGET, WOOD_OUTPUT_PROFILE_ITEMS
from .presets import get_preset_items


class MTreeQuickGenerateSettings(bpy.types.PropertyGroup):
    """Settings shared by the MTree sidebar and quick-generate operator."""

    preset: bpy.props.EnumProperty(
        name="Tree Type",
        description="Procedural species silhouette to generate",
        items=get_preset_items(),
        default="OAK",
    )
    seed: bpy.props.IntProperty(
        name="Seed",
        default=0,
        min=0,
        description="Random seed (0 chooses a new seed for each tree)",
    )
    wood_output_profile: bpy.props.EnumProperty(
        name="Wood Output",
        description="Choose original authoring topology or optimized game topology",
        items=WOOD_OUTPUT_PROFILE_ITEMS,
        default=ROBLOX_GAME_BUDGET,
    )
    overall_size: bpy.props.FloatProperty(
        name="Overall Size",
        description="Scale generated trunk height, branch length, and wood radius",
        default=1.0,
        min=0.25,
        max=3.0,
        soft_min=0.5,
        soft_max=2.0,
    )
    trunk_thickness: bpy.props.FloatProperty(
        name="Trunk Thickness",
        description="Scale trunk and connected branch thickness without adding radial rings",
        default=1.0,
        min=0.25,
        max=3.0,
        soft_min=0.5,
        soft_max=2.0,
    )
    branch_length: bpy.props.FloatProperty(
        name="Branch Length",
        description="Scale primary and secondary branch length",
        default=1.0,
        min=0.25,
        max=2.5,
        soft_min=0.5,
        soft_max=1.75,
    )
    branch_density: bpy.props.FloatProperty(
        name="Branch Density",
        description="Scale branch count; higher values can substantially increase topology",
        default=1.0,
        min=0.1,
        max=2.0,
        soft_min=0.5,
        soft_max=1.5,
    )
    branch_spread: bpy.props.FloatProperty(
        name="Branch Spread",
        description="Scale the starting angle of branches away from their parent",
        default=1.0,
        min=0.25,
        max=1.75,
        soft_min=0.5,
        soft_max=1.5,
    )
    branch_droop: bpy.props.FloatProperty(
        name="Branch Droop",
        description="Scale gravity acting on primary and secondary branches",
        default=1.0,
        min=0.0,
        max=3.0,
        soft_max=2.0,
    )
    randomness: bpy.props.FloatProperty(
        name="Randomness",
        description="Scale trunk and branch shape variation",
        default=1.0,
        min=0.0,
        max=2.0,
    )
    secondary_branches: bpy.props.BoolProperty(
        name="Secondary Branches",
        description="Generate the species secondary branch layer when one is defined",
        default=True,
    )
    add_leaves: bpy.props.BoolProperty(
        name="Add Legacy Leaves",
        description="Add original procedural leaves; foliage cards remain a separate operation",
        default=False,
    )


_OVERRIDE_FIELDS = (
    "overall_size",
    "trunk_thickness",
    "branch_length",
    "branch_density",
    "branch_spread",
    "branch_droop",
    "randomness",
)


def reset_generation_overrides(settings: MTreeQuickGenerateSettings) -> None:
    """Restore neutral focused overrides without changing species or seed."""

    for field_name in _OVERRIDE_FIELDS:
        setattr(settings, field_name, 1.0)
    settings.secondary_branches = True


def register():
    register_class(MTreeQuickGenerateSettings)
    bpy.types.Scene.mtree_quick_generate_settings = bpy.props.PointerProperty(
        type=MTreeQuickGenerateSettings
    )


def unregister():
    del bpy.types.Scene.mtree_quick_generate_settings
    unregister_class(MTreeQuickGenerateSettings)
