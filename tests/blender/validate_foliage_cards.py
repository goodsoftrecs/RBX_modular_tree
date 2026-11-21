"""Blender integration validation for complete-graph shallow-V foliage cards."""

from __future__ import annotations

import importlib
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


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
    foliage_cards = importlib.import_module(f"{repo_root.name}.python_classes.foliage_cards")
    foliage_layout = importlib.import_module(
        f"{repo_root.name}.python_classes.foliage_card_layout"
    )

    bpy.context.scene.mtree_foliage_library_set_id = "OAK"
    assert bpy.ops.mtree.create_foliage_card_template() == {"FINISHED"}
    library = bpy.data.collections.get("MTree_FoliageLibrary")
    assert library is not None
    set_collection = next(
        collection
        for collection in library.children
        if collection.get("mtree_foliage_set_id") == "OAK"
    )
    templates = sorted(
        (
            obj
            for obj in set_collection.objects
            if obj.get("mtree_role") == "FOLIAGE_CARD_TEMPLATE"
        ),
        key=lambda obj: obj.get("mtree_foliage_slot"),
    )
    assert len(templates) == 4
    assert all(template.type == "MESH" for template in templates)
    assert all(len(template.data.vertices) == 4 for template in templates)
    assert all(len(template.data.polygons) == 1 for template in templates)
    assert all(len(template.data.uv_layers) == 1 for template in templates)
    assert all(len(template.data.materials) == 1 for template in templates)
    shared_material = templates[0].data.materials[0]
    assert all(template.data.materials[0] is shared_material for template in templates)
    expected_bounds = {
        1: (0.0, 0.5, 0.5, 1.0),
        2: (0.5, 0.5, 1.0, 1.0),
        3: (0.0, 0.0, 0.5, 0.5),
        4: (0.5, 0.0, 1.0, 0.5),
    }
    for template in templates:
        slot = template.get("mtree_foliage_slot")
        minimum_u, minimum_v, maximum_u, maximum_v = expected_bounds[slot]
        assert all(
            minimum_u <= loop.uv.x <= maximum_u
            and minimum_v <= loop.uv.y <= maximum_v
            for loop in template.data.uv_layers.active.data
        )
    labels = [
        obj
        for obj in set_collection.objects
        if obj.get("mtree_role") == "FOLIAGE_CARD_SET_LABEL"
    ]
    assert len(labels) == 1 and labels[0].data.body == "Oak Foliage"
    template_meshes = [template.data for template in templates]

    # Initialization is idempotent and only adds a missing slot.
    assert bpy.ops.mtree.create_foliage_card_template() == {"FINISHED"}
    assert [template.data for template in templates] == template_meshes
    missing = templates.pop()
    missing_mesh = missing.data
    bpy.data.objects.remove(missing, do_unlink=True)
    if missing_mesh.users == 0:
        bpy.data.meshes.remove(missing_mesh)
    assert bpy.ops.mtree.create_foliage_card_template() == {"FINISHED"}
    repaired_templates = sorted(
        (
            obj
            for obj in set_collection.objects
            if obj.get("mtree_role") == "FOLIAGE_CARD_TEMPLATE"
        ),
        key=lambda obj: obj.get("mtree_foliage_slot"),
    )
    assert len(repaired_templates) == 4
    assert [template.data for template in repaired_templates[:3]] == template_meshes[:3]
    templates = repaired_templates

    # Every atlas slot pins its authored top-right UV point to the requested anchor.
    test_position = Vector((3.0, 4.0, 5.0))
    test_normal = Vector((0.0, 1.0, 0.0))
    test_placement = foliage_layout.CardPlacement(
        cluster_index=0,
        card_index=0,
        anchor_index=0,
        position=tuple(test_position),
        direction=(0.0, 0.0, 1.0),
        normal=tuple(test_normal),
        scale=2.0,
        template_slot=1,
    )
    for template in templates:
        slot = int(template.get("mtree_foliage_slot"))
        bounds = expected_bounds[slot]
        maximum_u, maximum_v = bounds[2], bounds[3]
        corner_indices = {
            template.data.loops[index].vertex_index
            for index, loop in enumerate(template.data.uv_layers.active.data)
            if abs(loop.uv.x - maximum_u) <= 1e-5
            and abs(loop.uv.y - maximum_v) <= 1e-5
        }
        assert corner_indices
        raw_attachment = sum(
            (template.data.vertices[index].co for index in corner_indices), Vector()
        ) / len(corner_indices)
        raw_center = sum(
            (vertex.co for vertex in template.data.vertices), Vector()
        ) / len(template.data.vertices)
        for branch_distance in (0.0, 0.35, -0.35):
            transform = foliage_cards._card_transform(
                template, test_placement, bounds, branch_distance
            )
            transformed_attachment = transform @ raw_attachment
            expected_attachment = test_position + test_normal * branch_distance
            assert (transformed_attachment - expected_attachment).length <= 1e-5
            transformed_center = transform @ raw_center
            outward = (transformed_center - transformed_attachment).normalized()
            assert outward.dot(Vector(test_placement.direction)) >= 1.0 - 1e-5

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
    assert wood.get("mtree_tree_species") == "OAK"
    assert wood.get("mtree_tree_number") == 1
    assert wood.get("mtree_role") == "WOOD"
    assert wood.get("mtree_generation_seed") == 538
    assert wood.mtree_foliage_seed == 538
    assert wood.mtree_foliage_set_id == "OAK"
    assert wood.mtree_foliage_cluster_count == 30
    assert wood.mtree_foliage_branch_distance == 0.0
    assert wood.mtree_foliage_texture_rotation == 0.0
    assert wood.mtree_foliage_pair_rotation == 0.0
    assert wood.mtree_foliage_canopy_rotation == 0.0
    assert (
        bpy.types.Object.bl_rna.properties["mtree_foliage_card_scale"].hard_max
        == 12.0
    )
    assert (
        bpy.types.Object.bl_rna.properties["mtree_foliage_branch_distance"].hard_min
        == -12.0
    )
    assert (
        bpy.types.Object.bl_rna.properties["mtree_foliage_branch_distance"].hard_max
        == 12.0
    )
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
    assert foliage.name == "Oak_1_Foliage"
    assert foliage.get("mtree_foliage_cluster_count") == 30
    assert foliage.get("mtree_foliage_card_count") == 60
    assert foliage.get("mtree_foliage_branch_distance") == 0.0
    missing_branch_count = foliage.get("mtree_foliage_missing_branch_count")
    missing_branch_clusters = foliage.get("mtree_foliage_missing_branch_clusters")
    physical_branch_clusters = foliage.get("mtree_foliage_physical_branch_clusters")
    assert missing_branch_count > 0
    assert missing_branch_clusters >= 0
    assert physical_branch_clusters >= 0
    assert missing_branch_clusters + physical_branch_clusters == 30
    variant_slots = list(foliage.get("mtree_foliage_variant_slots"))
    assert len(variant_slots) == 30
    assert set(variant_slots) == {1, 2, 3, 4}
    assert max(variant_slots.count(slot) for slot in range(1, 5)) - min(
        variant_slots.count(slot) for slot in range(1, 5)
    ) <= 1
    assert len(foliage.data.polygons) == 60
    assert sum(len(polygon.vertices) - 2 for polygon in foliage.data.polygons) == 120
    assert len(foliage.data.uv_layers) == 1
    assert len(foliage.data.materials) == 1
    first_vertices = [tuple(vertex.co) for vertex in foliage.data.vertices]
    first_uvs = [tuple(loop.uv) for loop in foliage.data.uv_layers.active.data]

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

    # Raising count appends branch-layer placements without moving or shrinking prior cards.
    wood.mtree_foliage_cluster_count = 40
    bpy.context.view_layer.objects.active = wood
    wood.select_set(True)
    refreshed.select_set(False)
    assert bpy.ops.mtree.refresh_foliage_cards() == {"FINISHED"}
    denser = next(
        obj
        for obj in bpy.data.objects
        if obj.get("mtree_tree_id") == tree_id and obj.get("mtree_role") == "FOLIAGE"
    )
    denser_vertices = [tuple(vertex.co) for vertex in denser.data.vertices]
    denser_uvs = [tuple(loop.uv) for loop in denser.data.uv_layers.active.data]
    assert denser.get("mtree_foliage_cluster_count") == 40
    assert denser.get("mtree_foliage_card_count") == 80
    assert denser_vertices[: len(first_vertices)] == first_vertices
    assert denser_uvs[: len(first_uvs)] == first_uvs

    wood.mtree_foliage_cluster_count = 30
    bpy.context.view_layer.objects.active = wood
    wood.select_set(True)
    denser.select_set(False)
    assert bpy.ops.mtree.refresh_foliage_cards() == {"FINISHED"}
    refreshed = next(
        obj
        for obj in bpy.data.objects
        if obj.get("mtree_tree_id") == tree_id and obj.get("mtree_role") == "FOLIAGE"
    )
    assert [tuple(vertex.co) for vertex in refreshed.data.vertices] == first_vertices

    # Template edits affect the next refresh without touching optimized wood.
    templates[0].data.vertices[2].co.x += 0.35
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

    # Per-tree appearance rotations affect UVs and geometry while remaining deterministic.
    wood.mtree_foliage_texture_rotation = math.radians(45.0)
    wood.mtree_foliage_pair_rotation = math.radians(30.0)
    wood.mtree_foliage_canopy_rotation = math.radians(90.0)
    wood.mtree_foliage_branch_distance = -0.25
    preview_material = templates[0].data.materials[0]
    image_node = preview_material.node_tree.nodes.new("ShaderNodeTexImage")
    image_node.image = bpy.data.images.new("FoliageControlValidation", width=2, height=2)
    bpy.context.view_layer.objects.active = wood
    wood.select_set(True)
    edited.select_set(False)
    assert bpy.ops.mtree.refresh_foliage_cards() == {"FINISHED"}
    controlled = next(
        obj
        for obj in bpy.data.objects
        if obj.get("mtree_tree_id") == tree_id and obj.get("mtree_role") == "FOLIAGE"
    )
    controlled_vertices = [tuple(vertex.co) for vertex in controlled.data.vertices]
    controlled_uvs = [tuple(loop.uv) for loop in controlled.data.uv_layers.active.data]
    assert controlled_vertices != first_vertices
    assert controlled_uvs != first_uvs
    assert all(0.0 <= component <= 1.0 for uv in controlled_uvs for component in uv)
    controlled_material = controlled.data.materials[0]
    assert controlled_material is not templates[0].data.materials[0]
    assert controlled_material.get("mtree_generated_foliage_material") is True
    assert all(
        node.extension == "CLIP"
        for node in controlled_material.node_tree.nodes
        if node.type == "TEX_IMAGE"
    )
    assert math.isclose(
        controlled.get("mtree_foliage_texture_rotation"),
        math.radians(45.0),
        abs_tol=1e-6,
    )
    assert math.isclose(
        controlled.get("mtree_foliage_pair_rotation"),
        math.radians(30.0),
        abs_tol=1e-6,
    )
    assert math.isclose(
        controlled.get("mtree_foliage_canopy_rotation"),
        math.radians(90.0),
        abs_tol=1e-6,
    )
    assert math.isclose(
        controlled.get("mtree_foliage_branch_distance"), -0.25, abs_tol=1e-6
    )

    bpy.context.view_layer.objects.active = controlled
    controlled.select_set(True)
    wood.select_set(False)
    assert bpy.ops.mtree.refresh_foliage_cards() == {"FINISHED"}
    edited = next(
        obj
        for obj in bpy.data.objects
        if obj.get("mtree_tree_id") == tree_id and obj.get("mtree_role") == "FOLIAGE"
    )
    assert [tuple(vertex.co) for vertex in edited.data.vertices] == controlled_vertices
    assert [tuple(loop.uv) for loop in edited.data.uv_layers.active.data] == controlled_uvs

    # Removing a required top-right UV corner fails before replacing valid foliage.
    corner_template = templates[2]
    corner_bounds = expected_bounds[int(corner_template.get("mtree_foliage_slot"))]
    corner_uvs = corner_template.data.uv_layers.active.data
    saved_corner_uvs = [tuple(loop.uv) for loop in corner_uvs]
    for loop in corner_uvs:
        if (
            abs(loop.uv.x - corner_bounds[2]) <= 1e-5
            and abs(loop.uv.y - corner_bounds[3]) <= 1e-5
        ):
            loop.uv.x -= 0.05
    bpy.context.view_layer.objects.active = wood
    wood.select_set(True)
    edited.select_set(False)
    assert bpy.ops.mtree.refresh_foliage_cards() == {"CANCELLED"}
    assert bpy.data.objects.get(edited.name) is edited
    for loop, saved_uv in zip(corner_uvs, saved_corner_uvs, strict=True):
        loop.uv = saved_uv

    # A material mismatch fails closed and preserves the prior generated object.
    mismatched_material = preview_material.copy()
    templates[3].data.materials[0] = mismatched_material
    bpy.context.view_layer.objects.active = wood
    wood.select_set(True)
    edited.select_set(False)
    assert bpy.ops.mtree.refresh_foliage_cards() == {"CANCELLED"}
    assert bpy.data.objects.get(edited.name) is edited
    templates[3].data.materials[0] = preview_material
    if mismatched_material.users == 0:
        bpy.data.materials.remove(mismatched_material)

    # A failed refresh must leave the last valid foliage object intact.
    saved_payload = wood[anchor_data.ANCHOR_PAYLOAD_KEY]
    wood[anchor_data.ANCHOR_PAYLOAD_KEY] = "corrupt"
    bpy.context.view_layer.objects.active = wood
    try:
        failed_result = bpy.ops.mtree.refresh_foliage_cards()
    except RuntimeError as error:
        assert "unsupported encoding" in str(error)
        failed_result = {"CANCELLED"}
    assert failed_result == {"CANCELLED"}
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
