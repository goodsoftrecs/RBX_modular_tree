"""Blender integration validation for complete-graph shallow-V foliage cards."""

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
    anchor_data = importlib.import_module(f"{repo_root.name}.python_classes.foliage_anchor_data")

    assert bpy.ops.mtree.create_foliage_card_template() == {"FINISHED"}
    library = bpy.data.collections.get("MTree_FoliageLibrary")
    template = bpy.data.objects.get("FoliageCard_Template")
    assert library is not None
    assert template is not None and template.type == "MESH"
    assert len(template.data.vertices) == 4
    assert len(template.data.polygons) == 1
    assert len(template.data.uv_layers) == 1
    assert len(template.data.materials) == 1
    template_mesh = template.data

    # Initialization is idempotent and preserves artist-controlled template data.
    assert bpy.ops.mtree.create_foliage_card_template() == {"FINISHED"}
    assert bpy.data.objects["FoliageCard_Template"].data is template_mesh

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
    assert wood.get("mtree_role") == "WOOD"
    assert wood.get("mtree_generation_seed") == 538
    assert wood.mtree_foliage_seed == 538
    assert wood.mtree_foliage_cluster_count == 30
    dense_anchors = anchor_data.load_anchor_payload(wood)
    assert dense_anchors
    assert max(anchor.hierarchy_depth for anchor in dense_anchors) > 0

    wood_vertices_before = [tuple(vertex.co) for vertex in wood.data.vertices]
    assert bpy.ops.mtree.refresh_foliage_cards() == {"FINISHED"}
    tree_id = wood.get("mtree_tree_id")
    foliage = next(
        obj
        for obj in bpy.data.objects
        if obj.get("mtree_tree_id") == tree_id and obj.get("mtree_role") == "FOLIAGE"
    )
    assert foliage.parent is wood.parent
    assert foliage.get("mtree_foliage_cluster_count") == 30
    assert foliage.get("mtree_foliage_card_count") == 60
    assert len(foliage.data.polygons) == 60
    assert sum(len(polygon.vertices) - 2 for polygon in foliage.data.polygons) == 120
    assert len(foliage.data.uv_layers) == 1
    assert len(foliage.data.materials) == 1
    first_vertices = [tuple(vertex.co) for vertex in foliage.data.vertices]

    # Refresh resolves through foliage selection and remains deterministic.
    bpy.context.view_layer.objects.active = foliage
    foliage.select_set(True)
    wood.select_set(False)
    assert bpy.ops.mtree.refresh_foliage_cards() == {"FINISHED"}
    refreshed = next(
        obj
        for obj in bpy.data.objects
        if obj.get("mtree_tree_id") == tree_id and obj.get("mtree_role") == "FOLIAGE"
    )
    assert [tuple(vertex.co) for vertex in refreshed.data.vertices] == first_vertices

    # Template edits affect the next refresh without touching optimized wood.
    template.data.vertices[2].co.x += 0.35
    bpy.context.view_layer.objects.active = wood
    wood.select_set(True)
    refreshed.select_set(False)
    assert bpy.ops.mtree.refresh_foliage_cards() == {"FINISHED"}
    edited = next(
        obj
        for obj in bpy.data.objects
        if obj.get("mtree_tree_id") == tree_id and obj.get("mtree_role") == "FOLIAGE"
    )
    assert [tuple(vertex.co) for vertex in edited.data.vertices] != first_vertices
    assert [tuple(vertex.co) for vertex in wood.data.vertices] == wood_vertices_before

    # A failed refresh must leave the last valid foliage object intact.
    saved_payload = wood[anchor_data.ANCHOR_PAYLOAD_KEY]
    wood[anchor_data.ANCHOR_PAYLOAD_KEY] = "corrupt"
    bpy.context.view_layer.objects.active = wood
    assert bpy.ops.mtree.refresh_foliage_cards() == {"CANCELLED"}
    assert bpy.data.objects.get(edited.name) is edited
    wood[anchor_data.ANCHOR_PAYLOAD_KEY] = saved_payload

    print(
        "FOLIAGE_CARDS "
        f"anchors={len(dense_anchors)} clusters={wood.mtree_foliage_cluster_count} "
        f"cards={edited.get('mtree_foliage_card_count')} triangles="
        f"{sum(len(polygon.vertices) - 2 for polygon in edited.data.polygons)}"
    )
finally:
    addon.unregister()
