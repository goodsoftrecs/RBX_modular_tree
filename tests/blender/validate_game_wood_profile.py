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

    def generate(profile: str):
        settings = SimpleNamespace(preset="OAK", wood_output_profile=profile)
        return operators.QuickGenerateTree._generate_tree(settings, 1234)

    authoring_mesh = generate(profiles.AUTHORING)
    game_mesh = generate(profiles.ROBLOX_GAME)

    authoring_counts = (
        len(authoring_mesh.get_vertices()) // 3,
        len(authoring_mesh.get_polygons()) // 4,
    )
    game_counts = (
        len(game_mesh.get_vertices()) // 3,
        len(game_mesh.get_polygons()) // 4,
    )
    polygon_ratio = game_counts[1] / authoring_counts[1]

    print(f"AUTHORING wood: vertices={authoring_counts[0]} polygons={authoring_counts[1]}")
    print(f"ROBLOX_GAME wood: vertices={game_counts[0]} polygons={game_counts[1]}")
    print(f"ROBLOX_GAME polygon ratio: {polygon_ratio:.3f}")

    assert game_counts[0] < authoring_counts[0]
    assert game_counts[1] < authoring_counts[1]
    assert polygon_ratio <= 0.50
finally:
    addon.unregister()
