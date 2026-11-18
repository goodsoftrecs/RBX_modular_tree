"""Blender integration validation for deterministic canopy lobes."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import bpy


repo_root = Path(__file__).resolve().parents[2]
native_path = os.environ.get("MTREE_NATIVE_PATH")
if not native_path:
    raise RuntimeError("MTREE_NATIVE_PATH must point to the unpacked native wheel")

sys.path.insert(0, native_path)
sys.path.insert(0, str(repo_root.parent))

addon = importlib.import_module(repo_root.name)
addon.register()

try:
    profiles = importlib.import_module(f"{repo_root.name}.python_classes.game_output_profiles")

    assert bpy.ops.mtree.create_canopy_lobes() == {"FINISHED"}
    library = bpy.data.collections.get("MTree_CanopyLibrary")
    assert library is not None
    template_names = ("Canopy_Round", "Canopy_Wide", "Canopy_Tip")
    templates = [bpy.data.objects.get(name) for name in template_names]
    assert all(template is not None for template in templates)
    assert all(template.type == "MESH" for template in templates)
    assert all(30 <= sum(len(poly.vertices) - 2 for poly in template.data.polygons) <= 60 for template in templates)
    template_meshes = [template.data for template in templates]

    # Initialization is idempotent and must preserve artist-edited template datablocks.
    assert bpy.ops.mtree.create_canopy_lobes() == {"FINISHED"}
    assert [bpy.data.objects.get(name).data for name in template_names] == template_meshes

    assert (
        bpy.ops.mtree.quick_generate(
            seed=538,
            preset="OAK",
            add_leaves=False,
            wood_output_profile=profiles.ROBLOX_GAME_BUDGET,
        )
        == {"FINISHED"}
    )
    wood = bpy.context.active_object
    assert wood is not None
    assert wood.name.startswith("Tree_0538_Wood")
    assert wood.get("mtree_role") == "WOOD"
    assert wood.get("mtree_generation_seed") == 538
    assert wood.mtree_canopy_seed == 538
    assert wood.mtree_lobe_count == 8
    assert wood.mtree_lobe_scale == 1.0
    assert any(collection.name.startswith("Tree_0538") for collection in wood.users_collection)

    wood_vertices_before = [tuple(vertex.co) for vertex in wood.data.vertices]
    assert bpy.ops.mtree.refresh_canopy_lobes() == {"FINISHED"}

    tree_id = wood.get("mtree_tree_id")
    foliage = next(
        obj
        for obj in bpy.data.objects
        if obj.get("mtree_tree_id") == tree_id and obj.get("mtree_role") == "FOLIAGE"
    )
    assert foliage.parent is wood.parent
    assert len(foliage.data.polygons) == 8 * 32
    assert len(foliage.data.uv_layers) == 1
    first_vertices = [tuple(vertex.co) for vertex in foliage.data.vertices]

    # Refresh is deterministic and can resolve from selected foliage.
    bpy.context.view_layer.objects.active = foliage
    foliage.select_set(True)
    wood.select_set(False)
    assert bpy.ops.mtree.refresh_canopy_lobes() == {"FINISHED"}
    refreshed_foliage = next(
        obj
        for obj in bpy.data.objects
        if obj.get("mtree_tree_id") == tree_id and obj.get("mtree_role") == "FOLIAGE"
    )
    assert [tuple(vertex.co) for vertex in refreshed_foliage.data.vertices] == first_vertices

    # Editing a reusable template changes only regenerated foliage, never wood.
    round_template = bpy.data.objects["Canopy_Round"]
    for vertex in round_template.data.vertices:
        vertex.co.x *= 1.25
    bpy.context.view_layer.objects.active = wood
    wood.select_set(True)
    refreshed_foliage.select_set(False)
    assert bpy.ops.mtree.refresh_canopy_lobes() == {"FINISHED"}
    resized_foliage = next(
        obj
        for obj in bpy.data.objects
        if obj.get("mtree_tree_id") == tree_id and obj.get("mtree_role") == "FOLIAGE"
    )
    assert [tuple(vertex.co) for vertex in resized_foliage.data.vertices] != first_vertices
    assert [tuple(vertex.co) for vertex in wood.data.vertices] == wood_vertices_before

    # A legacy Tree_<seed> mesh is adopted and receives its recoverable seed on first refresh.
    legacy = wood.copy()
    legacy.data = wood.data.copy()
    legacy.parent = None
    legacy.name = "Tree_777"
    for key in ("mtree_role", "mtree_tree_id", "mtree_generation_seed"):
        if key in legacy:
            del legacy[key]
    bpy.context.scene.collection.objects.link(legacy)
    bpy.context.view_layer.objects.active = legacy
    legacy.select_set(True)
    wood.select_set(False)
    assert bpy.ops.mtree.refresh_canopy_lobes() == {"FINISHED"}
    assert legacy.get("mtree_role") == "WOOD"
    assert legacy.get("mtree_generation_seed") == 777
    assert legacy.mtree_canopy_seed == 777
    assert any(collection.name.startswith("Tree_0777") for collection in legacy.users_collection)

    print(
        "CANOPY_LOBES "
        f"templates={len(templates)} lobes={wood.mtree_lobe_count} "
        f"vertices={len(resized_foliage.data.vertices)} "
        f"polygons={len(resized_foliage.data.polygons)}"
    )
finally:
    addon.unregister()
