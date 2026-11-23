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
    assert wood.name == "Oak_1_Wood"
    assert wood.get("mtree_role") == "WOOD"
    assert wood.get("mtree_generation_seed") == 538
    assert wood.get("mtree_tree_species") == "OAK"
    assert wood.get("mtree_tree_number") == 1
    assert wood.mtree_canopy_seed == 538
    assert wood.mtree_lobe_count == 8
    assert wood.mtree_lobe_scale == 1.0
    assert any(collection.name == "Oak_1" for collection in wood.users_collection)
    oak_collection = bpy.data.collections["Oak_1"]
    generated_root = bpy.data.collections["MTree_GeneratedTrees"]
    prefab_library = bpy.data.collections["RBX_PrefabLibrary_Placements"]
    assert oak_collection in list(generated_root.children)
    assert oak_collection in list(prefab_library.children)
    assert oak_collection["rbx_enabled"] is False
    assert oak_collection["rbx_prefab_key"] == "oak_1"
    assert oak_collection["rbx_category"] == "tree"
    assert oak_collection["rbx_alignment"] == "upright"
    anchors = [
        obj
        for obj in oak_collection.objects
        if obj.get("rbx_ground_anchor") is True
    ]
    assert len(anchors) == 1
    anchor = anchors[0]
    assert anchor.name == "RBX_GroundAnchor_Att"
    assert anchor.type == "EMPTY"
    assert anchor.parent is wood.parent
    assert tuple(anchor.location) == (0.0, 0.0, 0.0)

    # Repair is idempotent and preserves authored placement settings and anchor position.
    oak_collection["rbx_enabled"] = True
    anchor.location = (0.25, -0.5, 0.0)
    canopy_lobes = importlib.import_module(
        f"{repo_root.name}.python_classes.canopy_lobes"
    )
    canopy_lobes.organize_tree_object(wood)
    assert oak_collection["rbx_enabled"] is True
    assert tuple(anchor.location) == (0.25, -0.5, 0.0)
    assert len(
        [obj for obj in oak_collection.objects if obj.get("rbx_ground_anchor") is True]
    ) == 1

    # Numbering advances within a species and restarts for a different species.
    oak_two = wood.copy()
    oak_two.data = wood.data.copy()
    oak_two.parent = None
    for key in (
        "mtree_role",
        "mtree_tree_id",
        "mtree_generation_seed",
        "mtree_tree_species",
        "mtree_tree_number",
    ):
        if key in oak_two:
            del oak_two[key]
    bpy.context.scene.collection.objects.link(oak_two)
    canopy_lobes.organize_tree_object(
        oak_two, generation_seed=539, species_id="OAK", species_label="Oak"
    )
    assert oak_two.name == "Oak_2_Wood"
    assert oak_two.get("mtree_tree_number") == 2
    oak_two_collection = bpy.data.collections["Oak_2"]
    oak_two_anchor = next(
        obj for obj in oak_two_collection.objects if obj.get("rbx_ground_anchor") is True
    )
    assert oak_two_collection in list(prefab_library.children)
    assert oak_two_anchor.name == "RBX_GroundAnchor.001_Att"

    birch_one = wood.copy()
    birch_one.data = wood.data.copy()
    birch_one.parent = None
    for key in (
        "mtree_role",
        "mtree_tree_id",
        "mtree_generation_seed",
        "mtree_tree_species",
        "mtree_tree_number",
    ):
        if key in birch_one:
            del birch_one[key]
    bpy.context.scene.collection.objects.link(birch_one)
    canopy_lobes.organize_tree_object(
        birch_one, generation_seed=540, species_id="BIRCH", species_label="Birch"
    )
    assert birch_one.name == "Birch_1_Wood"
    assert birch_one.get("mtree_tree_number") == 1

    wood_vertices_before = [tuple(vertex.co) for vertex in wood.data.vertices]
    assert bpy.ops.mtree.refresh_canopy_lobes() == {"FINISHED"}

    tree_id = wood.get("mtree_tree_id")
    foliage = next(
        obj
        for obj in bpy.data.objects
        if obj.get("mtree_tree_id") == tree_id and obj.get("mtree_role") == "FOLIAGE"
    )
    assert foliage.parent is wood.parent
    assert foliage.name == "Oak_1_Foliage"
    assert foliage.get("mtree_tree_species") == "OAK"
    assert foliage.get("mtree_tree_number") == 1
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
