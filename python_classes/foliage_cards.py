"""Blender integration for editable branch-aligned foliage card pairs."""

from __future__ import annotations

import math

import bpy
from mathutils import Matrix, Vector

from .canopy_lobes import (
    GENERATED_TREES_NAME,
    ROLE_FOLIAGE,
    ROLE_KEY,
    SEED_KEY,
    TREE_ID_KEY,
    find_wood_for_object,
    organize_tree_object,
)
from .foliage_anchor_data import load_anchor_payload
from .foliage_card_layout import (
    CardPlacement,
    build_card_layout,
    rotate_card_layout_about_z,
    rotate_uv_to_fit,
)


FOLIAGE_LIBRARY_NAME = "MTree_FoliageLibrary"
FOLIAGE_TEMPLATE_NAME = "FoliageCard_Template"
FOLIAGE_PREVIEW_MATERIAL_NAME = "MTree_FoliagePreview"
ROLE_FOLIAGE_TEMPLATE = "FOLIAGE_CARD_TEMPLATE"
GENERATED_MATERIAL_KEY = "mtree_generated_foliage_material"


def _link_collection_to_scene(collection: bpy.types.Collection) -> None:
    scene = bpy.context.scene
    if collection.name not in {child.name for child in scene.collection.children}:
        scene.collection.children.link(collection)


def _get_or_create_library() -> bpy.types.Collection:
    collection = bpy.data.collections.get(FOLIAGE_LIBRARY_NAME)
    if collection is None:
        collection = bpy.data.collections.new(FOLIAGE_LIBRARY_NAME)
    _link_collection_to_scene(collection)
    collection.hide_viewport = False
    collection.hide_render = True
    return collection


def _preview_material() -> bpy.types.Material:
    material = bpy.data.materials.get(FOLIAGE_PREVIEW_MATERIAL_NAME)
    if material is None:
        material = bpy.data.materials.new(FOLIAGE_PREVIEW_MATERIAL_NAME)
        material.diffuse_color = (0.12, 0.48, 0.08, 1.0)
        material.roughness = 0.82
        material.use_nodes = True
        principled = material.node_tree.nodes.get("Principled BSDF")
        if principled is not None:
            principled.inputs["Base Color"].default_value = (0.12, 0.48, 0.08, 1.0)
            principled.inputs["Roughness"].default_value = 0.82
    return material


def _create_template_mesh() -> bpy.types.Mesh:
    """Create a unit card in local X/Z; +Z is the branch-following long axis."""

    mesh = bpy.data.meshes.new(FOLIAGE_TEMPLATE_NAME)
    mesh.from_pydata(
        [(-0.5, 0.0, 0.0), (0.5, 0.0, 0.0), (0.5, 0.0, 1.0), (-0.5, 0.0, 1.0)],
        [],
        [(0, 1, 2, 3)],
    )
    mesh.update(calc_edges=True)
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for loop_index, uv in enumerate(((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))):
        uv_layer.data[loop_index].uv = uv
    mesh.materials.append(_preview_material())
    return mesh


def ensure_foliage_card_template() -> tuple[bpy.types.Object, bool]:
    """Create the editable source card once without replacing artist edits."""

    collection = _get_or_create_library()
    template = bpy.data.objects.get(FOLIAGE_TEMPLATE_NAME)
    created = False
    if template is None:
        template = bpy.data.objects.new(FOLIAGE_TEMPLATE_NAME, _create_template_mesh())
        collection.objects.link(template)
        template.location = (0.0, -15.0, 1.0)
        created = True
    elif template.name not in collection.objects:
        collection.objects.link(template)

    if template.type != "MESH":
        raise ValueError(f"Foliage template '{FOLIAGE_TEMPLATE_NAME}' must be a mesh object")
    if len(template.data.vertices) < 3 or len(template.data.polygons) < 1:
        raise ValueError("Foliage card template must contain mesh geometry")
    if template.data.uv_layers.active is None:
        raise ValueError("Foliage card template must contain an active UV map")
    if len(template.data.materials) != 1 or template.data.materials[0] is None:
        raise ValueError("Foliage card template must use exactly one material")
    template[ROLE_KEY] = ROLE_FOLIAGE_TEMPLATE
    return template, created


def _find_tree_collection(tree_id: str) -> bpy.types.Collection | None:
    generated_root = bpy.data.collections.get(GENERATED_TREES_NAME)
    if generated_root is None:
        return None
    return next(
        (
            collection
            for collection in generated_root.children
            if collection.get(TREE_ID_KEY) == tree_id
        ),
        None,
    )


def _template_local_matrix(template: bpy.types.Object) -> Matrix:
    return template.rotation_euler.to_matrix().to_4x4() @ Matrix.Diagonal(
        (template.scale.x, template.scale.y, template.scale.z, 1.0)
    )


def _placement_matrix(placement: CardPlacement) -> Matrix:
    long_axis = Vector(placement.direction).normalized()
    normal = Vector(placement.normal).normalized()
    width_axis = normal.cross(long_axis).normalized()
    basis = Matrix(
        (
            (width_axis.x, normal.x, long_axis.x, 0.0),
            (width_axis.y, normal.y, long_axis.y, 0.0),
            (width_axis.z, normal.z, long_axis.z, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )
    )
    return (
        Matrix.Translation(placement.position)
        @ basis
        @ Matrix.Scale(placement.scale, 4)
    )


def _build_foliage_mesh(
    template: bpy.types.Object,
    placements: list[CardPlacement],
    texture_rotation_radians: float = 0.0,
    output_material: bpy.types.Material | None = None,
) -> bpy.types.Mesh:
    source_mesh = template.data
    source_uv = source_mesh.uv_layers.active
    if source_uv is None:
        raise ValueError("Foliage card template must contain an active UV map")

    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    face_uvs: list[list[tuple[float, float]]] = []
    template_matrix = _template_local_matrix(template)

    for placement in placements:
        transform = _placement_matrix(placement) @ template_matrix
        vertex_offset = len(vertices)
        vertices.extend(tuple(transform @ vertex.co) for vertex in source_mesh.vertices)
        for polygon in source_mesh.polygons:
            faces.append(tuple(vertex_offset + index for index in polygon.vertices))
            face_uvs.append(
                [
                    rotate_uv_to_fit(
                        tuple(source_uv.data[index].uv), texture_rotation_radians
                    )
                    for index in polygon.loop_indices
                ]
            )

    mesh = bpy.data.meshes.new("Foliage_Cards")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for polygon, uvs in zip(mesh.polygons, face_uvs, strict=True):
        for loop_index, uv in zip(polygon.loop_indices, uvs, strict=True):
            uv_layer.data[loop_index].uv = uv
    mesh.materials.append(output_material or source_mesh.materials[0])
    return mesh


def _material_for_texture_rotation(
    template_material: bpy.types.Material,
    texture_rotation_radians: float,
    tree_name: str,
) -> bpy.types.Material | None:
    """Create the clipped tree-owned material required by fitted rotated UVs."""

    if abs(math.remainder(texture_rotation_radians, math.tau)) <= 1e-12:
        return None
    if not template_material.use_nodes or template_material.node_tree is None:
        raise ValueError("Texture Rotation requires a node-based template material")
    image_nodes = [
        node for node in template_material.node_tree.nodes if node.type == "TEX_IMAGE"
    ]
    if not image_nodes:
        return None

    material = template_material.copy()
    material.name = f"{tree_name}_FoliageMaterial"
    material[GENERATED_MATERIAL_KEY] = True
    for node in material.node_tree.nodes:
        if node.type == "TEX_IMAGE":
            node.extension = "CLIP"
    return material


def _remove_generated_material_if_unused(material: bpy.types.Material | None) -> None:
    if (
        material is not None
        and material.get(GENERATED_MATERIAL_KEY)
        and material.users == 0
    ):
        bpy.data.materials.remove(material)


def refresh_foliage_cards_for_object(
    active_object: bpy.types.Object | None,
) -> tuple[bpy.types.Object, int, int]:
    """Build new foliage completely before replacing the selected tree's old output."""

    wood = find_wood_for_object(active_object)
    if wood is None:
        raise ValueError("Select an MTree-generated wood or foliage object")
    wood = organize_tree_object(wood)
    tree_id = str(wood[TREE_ID_KEY])
    tree_collection = _find_tree_collection(tree_id)
    if tree_collection is None:
        raise ValueError("Selected tree has no owning collection")

    template, _ = ensure_foliage_card_template()
    anchors = load_anchor_payload(wood)
    placements = build_card_layout(
        anchors,
        cluster_count=int(wood.mtree_foliage_cluster_count),
        scale_multiplier=float(wood.mtree_foliage_card_scale),
        seed=int(wood.mtree_foliage_seed),
        pair_rotation_radians=float(wood.mtree_foliage_pair_rotation),
    )
    placements = rotate_card_layout_about_z(
        placements, float(wood.mtree_foliage_canopy_rotation)
    )
    texture_rotation = float(wood.mtree_foliage_texture_rotation)
    generated_material = _material_for_texture_rotation(
        template.data.materials[0], texture_rotation, tree_collection.name
    )
    try:
        new_mesh = _build_foliage_mesh(
            template,
            placements,
            texture_rotation_radians=texture_rotation,
            output_material=generated_material,
        )
    except Exception:
        _remove_generated_material_if_unused(generated_material)
        raise
    expected_cards = int(wood.mtree_foliage_cluster_count) * 2
    if len(placements) != expected_cards or len(new_mesh.polygons) < expected_cards:
        bpy.data.meshes.remove(new_mesh)
        _remove_generated_material_if_unused(generated_material)
        raise ValueError("Generated foliage card mesh failed validation")

    foliage = bpy.data.objects.new(f"{tree_collection.name}_Foliage_New", new_mesh)
    tree_collection.objects.link(foliage)
    foliage.parent = wood.parent
    foliage.matrix_local = wood.matrix_local.copy()
    foliage[ROLE_KEY] = ROLE_FOLIAGE
    foliage[TREE_ID_KEY] = tree_id
    foliage[SEED_KEY] = int(wood.mtree_foliage_seed)
    foliage["mtree_foliage_cluster_count"] = int(wood.mtree_foliage_cluster_count)
    foliage["mtree_foliage_card_count"] = len(placements)
    foliage["mtree_foliage_texture_rotation"] = float(
        wood.mtree_foliage_texture_rotation
    )
    foliage["mtree_foliage_pair_rotation"] = float(wood.mtree_foliage_pair_rotation)
    foliage["mtree_foliage_canopy_rotation"] = float(
        wood.mtree_foliage_canopy_rotation
    )

    old_foliage = [
        obj
        for obj in list(tree_collection.objects)
        if obj != foliage and obj.get(ROLE_KEY) == ROLE_FOLIAGE
    ]
    for old in old_foliage:
        old_mesh = old.data if old.type == "MESH" else None
        old_materials = list(old_mesh.materials) if old_mesh is not None else []
        bpy.data.objects.remove(old, do_unlink=True)
        if old_mesh is not None and old_mesh.users == 0:
            bpy.data.meshes.remove(old_mesh)
        for material in old_materials:
            _remove_generated_material_if_unused(material)

    if generated_material is not None:
        generated_material.name = f"{tree_collection.name}_FoliageMaterial"
    foliage.name = f"{tree_collection.name}_Foliage"
    new_mesh.name = foliage.name
    return foliage, int(wood.mtree_foliage_cluster_count), len(placements)


def register_properties() -> None:
    bpy.types.Object.mtree_foliage_cluster_count = bpy.props.IntProperty(
        name="Foliage Cluster Count",
        description="Exact number of shallow-V foliage card pairs",
        default=30,
        min=1,
        max=256,
    )
    bpy.types.Object.mtree_foliage_card_scale = bpy.props.FloatProperty(
        name="Card Scale",
        description="Multiplier over the automatically derived foliage card size",
        default=1.0,
        min=0.1,
        max=12.0,
    )
    bpy.types.Object.mtree_foliage_texture_rotation = bpy.props.FloatProperty(
        name="Texture Rotation",
        description="Rotate and fit the complete foliage texture inside every card",
        subtype="ANGLE",
        default=0.0,
        min=-math.tau,
        max=math.tau,
    )
    bpy.types.Object.mtree_foliage_pair_rotation = bpy.props.FloatProperty(
        name="Card Pair Rotation",
        description="Roll each shallow-V card pair around its virtual branch direction",
        subtype="ANGLE",
        default=0.0,
        min=-math.tau,
        max=math.tau,
    )
    bpy.types.Object.mtree_foliage_canopy_rotation = bpy.props.FloatProperty(
        name="Canopy Rotation",
        description="Rotate the complete foliage canopy around the tree-local Z axis",
        subtype="ANGLE",
        default=0.0,
        min=-math.tau,
        max=math.tau,
    )
    bpy.types.Object.mtree_foliage_seed = bpy.props.IntProperty(
        name="Foliage Seed",
        description="Deterministic foliage anchor selection and card variation seed",
        default=0,
        min=0,
    )


def unregister_properties() -> None:
    for name in (
        "mtree_foliage_seed",
        "mtree_foliage_canopy_rotation",
        "mtree_foliage_pair_rotation",
        "mtree_foliage_texture_rotation",
        "mtree_foliage_card_scale",
        "mtree_foliage_cluster_count",
    ):
        if hasattr(bpy.types.Object, name):
            delattr(bpy.types.Object, name)
