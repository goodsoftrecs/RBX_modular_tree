"""Validate quick-generation species, defaults, overrides, and topology budgets."""

from __future__ import annotations

import importlib
import math
import os
import sys
from pathlib import Path
from types import SimpleNamespace


repo_root = Path(__file__).resolve().parents[2]
native_path = os.environ.get("MTREE_NATIVE_PATH")
if not native_path:
    raise RuntimeError("MTREE_NATIVE_PATH must point to the unpacked native wheel")

sys.path.insert(0, native_path)
sys.path.insert(0, str(repo_root.parent))

addon = importlib.import_module(repo_root.name)
addon.register()

try:
    import bpy

    operators = importlib.import_module(f"{repo_root.name}.python_classes.operators")
    presets = importlib.import_module(
        f"{repo_root.name}.python_classes.presets.tree_presets"
    )
    profiles = importlib.import_module(
        f"{repo_root.name}.python_classes.game_output_profiles"
    )

    settings = bpy.context.scene.mtree_quick_generate_settings
    assert settings.preset == "OAK"
    assert settings.wood_output_profile == profiles.ROBLOX_GAME_BUDGET

    def generation_settings(preset: str, **overrides):
        values = {
            "preset": preset,
            "wood_output_profile": profiles.ROBLOX_GAME_BUDGET,
            "overall_size": 1.0,
            "trunk_thickness": 1.0,
            "branch_length": 1.0,
            "branch_density": 1.0,
            "branch_spread": 1.0,
            "branch_droop": 1.0,
            "randomness": 1.0,
            "secondary_branches": True,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def triangle_count(mesh):
        polygons = mesh.get_polygons()
        return sum(
            1 if polygons[index + 2] == polygons[index + 3] else 2
            for index in range(0, len(polygons), 4)
        )

    authored_species = tuple(name for name in presets.TREE_PRESETS if name != "RANDOM")
    assert authored_species == (
        "OAK",
        "BIRCH",
        "PINE",
        "CEDAR",
        "WALNUT",
        "SEQUOIA",
        "HEMLOCK",
        "TEAK",
        "DEAD_SNAG",
    )

    counts = {}
    over_budget = []
    for preset in authored_species:
        mesh, anchors = operators.QuickGenerateTree._generate_tree(
            generation_settings(preset), 1234
        )
        counts[preset] = triangle_count(mesh)
        print(f"SPECIES {preset}: triangles={counts[preset]} anchors={len(anchors)}")
        assert counts[preset] > 0
        if counts[preset] > 4500:
            over_budget.append((preset, counts[preset]))
        assert len(anchors) > 0

    assert not over_budget, f"Stock species above 4.5K triangles: {over_budget}"

    oak_default, _ = operators.QuickGenerateTree._generate_tree(
        generation_settings("OAK"), 1234
    )
    oak_thick, _ = operators.QuickGenerateTree._generate_tree(
        generation_settings("OAK", trunk_thickness=2.0), 1234
    )
    assert triangle_count(oak_thick) == triangle_count(oak_default)

    oak_no_secondary, _ = operators.QuickGenerateTree._generate_tree(
        generation_settings("OAK", secondary_branches=False), 1234
    )
    assert triangle_count(oak_no_secondary) <= triangle_count(oak_default)

    # Exercise the persistent sidebar bridge and a bounded foliage-card refresh.
    settings.preset = "CEDAR"
    settings.seed = 2024
    settings.overall_size = 0.75
    settings.trunk_thickness = 1.5
    settings.branch_density = 0.8
    print("SIDEBAR_GENERATION_START", flush=True)
    assert (
        bpy.ops.mtree.quick_generate("INVOKE_DEFAULT", use_sidebar_settings=True)
        == {"FINISHED"}
    )
    wood = bpy.context.active_object
    assert wood.get("mtree_generation_preset") == "CEDAR"
    assert wood.get("mtree_wood_output_profile") == profiles.ROBLOX_GAME_BUDGET
    assert math.isclose(wood.get("mtree_overall_size"), 0.75, abs_tol=1e-6)
    assert math.isclose(wood.get("mtree_trunk_thickness"), 1.5, abs_tol=1e-6)
    assert math.isclose(wood.get("mtree_branch_density"), 0.8, abs_tol=1e-6)
    print("SIDEBAR_GENERATION_OK", flush=True)

    assert bpy.ops.mtree.create_foliage_card_template() == {"FINISHED"}
    assert bpy.ops.mtree.refresh_foliage_cards() == {"FINISHED"}
    foliage = next(
        obj
        for obj in bpy.data.objects
        if obj.get("mtree_tree_id") == wood.get("mtree_tree_id")
        and obj.get("mtree_role") == "FOLIAGE"
    )
    assert foliage.get("mtree_foliage_card_count") == 60
    assert sum(len(polygon.vertices) - 2 for polygon in foliage.data.polygons) == 120
    print("SIDEBAR_FOLIAGE_OK", flush=True)

    print("SPECIES_GENERATION_OK")
finally:
    addon.unregister()
