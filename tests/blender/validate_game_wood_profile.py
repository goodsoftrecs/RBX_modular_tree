"""Blender integration check for the low-detail Roblox wood profile.

Run with Blender in background mode and set MTREE_NATIVE_PATH to an unpacked
official MTree wheel matching Blender's Python version.
"""

from __future__ import annotations

import importlib
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
    operators = importlib.import_module(f"{repo_root.name}.python_classes.operators")
    profiles = importlib.import_module(
        f"{repo_root.name}.python_classes.game_output_profiles"
    )

    def generate(profile: str, preset: str = "OAK"):
        settings = SimpleNamespace(preset=preset, wood_output_profile=profile)
        return operators.QuickGenerateTree._generate_tree(settings, 1234)

    def mesh_counts(mesh):
        return (len(mesh.get_vertices()) // 3, len(mesh.get_polygons()) // 4)

    def triangle_count(mesh):
        polygons = mesh.get_polygons()
        return sum(
            1 if polygons[index + 2] == polygons[index + 3] else 2
            for index in range(0, len(polygons), 4)
        )

    authoring_mesh = generate(profiles.AUTHORING)
    game_mesh = generate(profiles.ROBLOX_GAME)
    budget_mesh = generate(profiles.ROBLOX_GAME_BUDGET)

    authoring_counts = mesh_counts(authoring_mesh)
    game_counts = mesh_counts(game_mesh)
    budget_counts = mesh_counts(budget_mesh)
    polygon_ratio = game_counts[1] / authoring_counts[1]

    print(f"AUTHORING wood: vertices={authoring_counts[0]} polygons={authoring_counts[1]}")
    print(f"ROBLOX_GAME wood: vertices={game_counts[0]} polygons={game_counts[1]}")
    print(f"ROBLOX_GAME polygon ratio: {polygon_ratio:.3f}")
    print(
        f"ROBLOX_GAME_BUDGET wood: vertices={budget_counts[0]} "
        f"polygons={budget_counts[1]} triangles={triangle_count(budget_mesh)}"
    )

    assert game_counts[0] < authoring_counts[0]
    assert game_counts[1] < authoring_counts[1]
    assert polygon_ratio <= 0.50
    for seed in (42, 1234, 6676, 9999):
        seed_budget_mesh = operators.QuickGenerateTree._generate_tree(
            SimpleNamespace(preset="OAK", wood_output_profile=profiles.ROBLOX_GAME_BUDGET),
            seed,
        )
        seed_triangle_count = triangle_count(seed_budget_mesh)
        print(f"OAK seed={seed} budget triangles={seed_triangle_count}")
        assert 2500 <= seed_triangle_count <= 4000

    for preset in ("PINE", "WILLOW"):
        preset_authoring_counts = mesh_counts(generate(profiles.AUTHORING, preset))
        preset_budget_counts = mesh_counts(generate(profiles.ROBLOX_GAME_BUDGET, preset))
        print(
            f"{preset} budget wood: vertices={preset_budget_counts[0]} "
            f"polygons={preset_budget_counts[1]}"
        )
        assert 0 < preset_budget_counts[1] < preset_authoring_counts[1]
finally:
    addon.unregister()
