"""Blender integration for editable low-poly canopy lobe templates and outputs."""

from __future__ import annotations

import math
import re
import uuid
from collections import defaultdict

import bpy
from mathutils import Euler, Matrix, Vector

from .canopy_layout import Anchor, build_lobe_layout


CANOPY_LIBRARY_NAME = "MTree_CanopyLibrary"
GENERATED_TREES_NAME = "MTree_GeneratedTrees"
PREVIEW_MATERIAL_NAME = "MTree_CanopyPreview"
TEMPLATE_NAMES = ("Canopy_Round", "Canopy_Wide", "Canopy_Tip")

ROLE_KEY = "mtree_role"
TREE_ID_KEY = "mtree_tree_id"
SEED_KEY = "mtree_generation_seed"
TREE_SPECIES_KEY = "mtree_tree_species"
TREE_NUMBER_KEY = "mtree_tree_number"
ROLE_ROOT = "ROOT"
ROLE_WOOD = "WOOD"
ROLE_FOLIAGE = "FOLIAGE"
ROLE_TEMPLATE = "CANOPY_TEMPLATE"


def _link_collection_to_scene(collection: bpy.types.Collection) -> None:
    scene = bpy.context.scene
    if collection.name not in {child.name for child in scene.collection.children}:
        scene.collection.children.link(collection)


def _get_or_create_top_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
    _link_collection_to_scene(collection)
    return collection


def _preview_material() -> bpy.types.Material:
    material = bpy.data.materials.get(PREVIEW_MATERIAL_NAME)
    if material is None:
        material = bpy.data.materials.new(PREVIEW_MATERIAL_NAME)
        material.diffuse_color = (0.12, 0.42, 0.08, 1.0)
        material.roughness = 0.85
    return material


def _template_profile(name: str) -> tuple[float, float, float, tuple[float, float, float]]:
    if name == "Canopy_Wide":
        return (1.45, 0.82, 0.58, (0.03, -0.04, 0.0))
    if name == "Canopy_Tip":
        return (0.72, 0.72, 1.08, (-0.02, 0.02, 0.08))
    return (1.0, 0.92, 0.76, (0.0, 0.0, 0.0))


def _create_template_mesh(name: str) -> bpy.types.Mesh:
    """Create a closed 48-triangle, UV-mapped irregular lobe."""

    x_scale, y_scale, z_scale, offset = _template_profile(name)
    segments = 8
    ring_z = (-0.55, -0.02, 0.52)
    ring_radius = (0.72, 1.0, 0.68)
    if name == "Canopy_Tip":
        ring_z = (-0.68, -0.12, 0.55)
        ring_radius = (0.82, 1.0, 0.52)

    vertices: list[tuple[float, float, float]] = [(offset[0], offset[1], -z_scale + offset[2])]
    for ring_index, (z_value, radius) in enumerate(zip(ring_z, ring_radius, strict=True)):
        for segment in range(segments):
            angle = 2.0 * math.pi * segment / segments
            irregularity = 1.0 + 0.08 * math.sin(
                segment * 2.37 + ring_index * 1.91 + len(name)
            )
            vertices.append(
                (
                    math.cos(angle) * x_scale * radius * irregularity + offset[0],
                    math.sin(angle) * y_scale * radius * irregularity + offset[1],
                    z_value * z_scale + offset[2],
                )
            )
    top_index = len(vertices)
    vertices.append((offset[0], offset[1], z_scale + offset[2]))

    faces: list[tuple[int, ...]] = []
    first_ring = 1
    for segment in range(segments):
        next_segment = (segment + 1) % segments
        faces.append((0, first_ring + next_segment, first_ring + segment))

    for ring_index in range(len(ring_z) - 1):
        current = first_ring + ring_index * segments
        following = current + segments
        for segment in range(segments):
            next_segment = (segment + 1) % segments
            faces.append(
                (
                    current + segment,
                    current + next_segment,
                    following + next_segment,
                    following + segment,
                )
            )

    last_ring = first_ring + (len(ring_z) - 1) * segments
    for segment in range(segments):
        next_segment = (segment + 1) % segments
        faces.append((last_ring + segment, last_ring + next_segment, top_index))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    for polygon in mesh.polygons:
        polygon.use_smooth = True

    uv_layer = mesh.uv_layers.new(name="UVMap")
    z_min = min(vertex[2] for vertex in vertices)
    z_max = max(vertex[2] for vertex in vertices)
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            vertex = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            u = (math.atan2(vertex.y - offset[1], vertex.x - offset[0]) / (2.0 * math.pi)) % 1.0
            v = (vertex.z - z_min) / max(z_max - z_min, 1e-6)
            uv_layer.data[loop_index].uv = (u, v)

    mesh.materials.append(_preview_material())
    return mesh


def ensure_canopy_templates() -> tuple[list[bpy.types.Object], int]:
    """Create missing editable templates and preserve all existing template objects."""

    collection = _get_or_create_top_collection(CANOPY_LIBRARY_NAME)
    collection.hide_viewport = False
    collection.hide_render = True
    templates: list[bpy.types.Object] = []
    created = 0

    display_locations = {
        "Canopy_Round": (-3.0, -15.0, 1.0),
        "Canopy_Wide": (0.0, -15.0, 1.0),
        "Canopy_Tip": (3.0, -15.0, 1.0),
    }
    for name in TEMPLATE_NAMES:
        obj = bpy.data.objects.get(name)
        if obj is None:
            obj = bpy.data.objects.new(name, _create_template_mesh(name))
            collection.objects.link(obj)
            obj.location = display_locations[name]
            created += 1
        elif obj.name not in collection.objects:
            collection.objects.link(obj)
        if obj.type != "MESH":
            raise ValueError(f"Canopy template '{name}' must be a mesh object")
        obj[ROLE_KEY] = ROLE_TEMPLATE
        templates.append(obj)

    return templates, created


def _parse_seed(name: str) -> int:
    match = re.search(r"Tree_(\d+)", name)
    return int(match.group(1)) if match else 0


def _species_display_name(label: str) -> str:
    display_name = re.sub(r"[^A-Za-z0-9]+", "_", str(label)).strip("_")
    return display_name or "Tree"


def _next_species_tree_number(
    generated_root: bpy.types.Collection, species_id: str, display_name: str
) -> int:
    existing_numbers = [
        int(collection.get(TREE_NUMBER_KEY))
        for collection in generated_root.children
        if collection.get(TREE_SPECIES_KEY) == species_id
        and int(collection.get(TREE_NUMBER_KEY, 0)) > 0
    ]
    number = max(existing_numbers, default=0) + 1
    while (
        bpy.data.collections.get(f"{display_name}_{number}") is not None
        or bpy.data.objects.get(f"{display_name}_{number}_Root") is not None
        or bpy.data.objects.get(f"{display_name}_{number}_Wood") is not None
    ):
        number += 1
    return number


def _is_tree_mesh(obj: bpy.types.Object | None) -> bool:
    return bool(
        obj
        and obj.type == "MESH"
        and hasattr(obj.data, "attributes")
        and "radius" in obj.data.attributes
        and "direction" in obj.data.attributes
    )


def _find_tree_collection(tree_id: str) -> bpy.types.Collection | None:
    return next(
        (collection for collection in bpy.data.collections if collection.get(TREE_ID_KEY) == tree_id),
        None,
    )


def _find_role_object(tree_id: str, role: str) -> bpy.types.Object | None:
    return next(
        (
            obj
            for obj in bpy.data.objects
            if obj.get(TREE_ID_KEY) == tree_id and obj.get(ROLE_KEY) == role
        ),
        None,
    )


def find_wood_for_object(obj: bpy.types.Object | None) -> bpy.types.Object | None:
    if obj is None:
        return None
    if obj.get(ROLE_KEY) == ROLE_WOOD and _is_tree_mesh(obj):
        return obj
    tree_id = obj.get(TREE_ID_KEY)
    if tree_id:
        return _find_role_object(tree_id, ROLE_WOOD)
    if _is_tree_mesh(obj):
        return obj
    return None


def organize_tree_object(
    wood: bpy.types.Object,
    generation_seed: int | None = None,
    species_id: str | None = None,
    species_label: str | None = None,
) -> bpy.types.Object:
    """Add stable ownership and move a generated or legacy wood mesh into its tree collection."""

    if not _is_tree_mesh(wood):
        raise ValueError("Select an MTree-generated wood mesh")
    if wood.get(ROLE_KEY) == ROLE_WOOD and wood.get(TREE_ID_KEY):
        return wood

    seed = int(generation_seed if generation_seed is not None else _parse_seed(wood.name))
    tree_id = str(uuid.uuid4())
    generated_root = _get_or_create_top_collection(GENERATED_TREES_NAME)
    tree_number = None
    if species_id is not None:
        normalized_species = str(species_id).upper()
        display_name = _species_display_name(species_label or normalized_species.title())
        tree_number = _next_species_tree_number(
            generated_root, normalized_species, display_name
        )
        collection_name = f"{display_name}_{tree_number}"
    else:
        normalized_species = None
        collection_name = f"Tree_{seed:04d}"

    tree_collection = bpy.data.collections.new(collection_name)
    generated_root.children.link(tree_collection)
    tree_collection[TREE_ID_KEY] = tree_id
    tree_collection[SEED_KEY] = seed
    if normalized_species is not None and tree_number is not None:
        tree_collection[TREE_SPECIES_KEY] = normalized_species
        tree_collection[TREE_NUMBER_KEY] = tree_number

    root = bpy.data.objects.new(f"{tree_collection.name}_Root", None)
    tree_collection.objects.link(root)
    root[ROLE_KEY] = ROLE_ROOT
    root[TREE_ID_KEY] = tree_id
    root[SEED_KEY] = seed
    if normalized_species is not None and tree_number is not None:
        root[TREE_SPECIES_KEY] = normalized_species
        root[TREE_NUMBER_KEY] = tree_number

    if wood.name not in tree_collection.objects:
        tree_collection.objects.link(wood)
    for collection in list(wood.users_collection):
        if collection != tree_collection:
            collection.objects.unlink(wood)

    wood.name = f"{tree_collection.name}_Wood"
    wood[ROLE_KEY] = ROLE_WOOD
    wood[TREE_ID_KEY] = tree_id
    wood[SEED_KEY] = seed
    if normalized_species is not None and tree_number is not None:
        wood[TREE_SPECIES_KEY] = normalized_species
        wood[TREE_NUMBER_KEY] = tree_number
    wood.parent = root
    wood.mtree_lobe_count = 8
    wood.mtree_lobe_scale = 1.0
    wood.mtree_canopy_seed = seed
    if hasattr(wood, "mtree_foliage_cluster_count"):
        wood.mtree_foliage_cluster_count = 30
        wood.mtree_foliage_card_scale = 1.0
        wood.mtree_foliage_branch_distance = 0.0
        wood.mtree_foliage_texture_rotation = 0.0
        wood.mtree_foliage_pair_rotation = 0.0
        wood.mtree_foliage_canopy_rotation = 0.0
        wood.mtree_foliage_seed = seed
    return wood


def _extract_branch_anchors(wood: bpy.types.Object) -> list[Anchor]:
    mesh = wood.data
    required = ("stem_id", "hierarchy_depth", "pivot_position", "direction")
    missing = [name for name in required if name not in mesh.attributes]
    if missing:
        raise ValueError(f"Tree wood is missing canopy attributes: {', '.join(missing)}")

    stem_attr = mesh.attributes["stem_id"].data
    depth_attr = mesh.attributes["hierarchy_depth"].data
    pivot_attr = mesh.attributes["pivot_position"].data
    direction_attr = mesh.attributes["direction"].data
    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(mesh.vertices)):
        groups[int(round(stem_attr[index].value))].append(index)

    anchors: list[Anchor] = []
    for stem_id, indices in groups.items():
        depth = int(round(max(depth_attr[index].value for index in indices)))
        if stem_id == 0 or depth <= 0:
            continue
        endpoint_index = max(
            indices,
            key=lambda index: (
                mesh.vertices[index].co - Vector(pivot_attr[index].vector)
            ).length_squared,
        )
        vertex = mesh.vertices[endpoint_index].co
        direction = direction_attr[endpoint_index].vector
        anchors.append(
            Anchor(
                position=(float(vertex.x), float(vertex.y), float(vertex.z)),
                direction=(float(direction[0]), float(direction[1]), float(direction[2])),
                depth=depth,
            )
        )

    if not anchors:
        raise ValueError("Tree wood has no retained branch endpoints for canopy placement")
    return anchors


def _template_local_matrix(template: bpy.types.Object) -> Matrix:
    return template.rotation_euler.to_matrix().to_4x4() @ Matrix.Diagonal(
        (template.scale.x, template.scale.y, template.scale.z, 1.0)
    )


def _build_foliage_mesh(templates: dict[str, bpy.types.Object], placements) -> bpy.types.Mesh:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    face_uvs: list[list[tuple[float, float]]] = []

    for placement in placements:
        template = templates[placement.template_name]
        source_mesh = template.data
        transform = (
            Matrix.Translation(placement.position)
            @ Euler(placement.rotation, "XYZ").to_matrix().to_4x4()
            @ Matrix.Scale(placement.scale, 4)
            @ _template_local_matrix(template)
        )
        vertex_offset = len(vertices)
        vertices.extend(tuple(transform @ vertex.co) for vertex in source_mesh.vertices)

        source_uv = source_mesh.uv_layers.active
        for polygon in source_mesh.polygons:
            faces.append(tuple(vertex_offset + index for index in polygon.vertices))
            if source_uv is None:
                face_uvs.append([(0.0, 0.0)] * len(polygon.vertices))
            else:
                face_uvs.append(
                    [tuple(source_uv.data[index].uv) for index in polygon.loop_indices]
                )

    mesh = bpy.data.meshes.new("Canopy_Foliage")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    for polygon in mesh.polygons:
        polygon.use_smooth = True

    uv_layer = mesh.uv_layers.new(name="UVMap")
    for polygon, uvs in zip(mesh.polygons, face_uvs, strict=True):
        for loop_index, uv in zip(polygon.loop_indices, uvs, strict=True):
            uv_layer.data[loop_index].uv = uv
    mesh.materials.append(_preview_material())
    return mesh


def refresh_canopy_for_object(active_object: bpy.types.Object | None) -> tuple[bpy.types.Object, int]:
    """Generate or safely replace the selected tree's combined foliage mesh."""

    wood = find_wood_for_object(active_object)
    if wood is None:
        raise ValueError("Select an MTree-generated wood or foliage object")
    wood = organize_tree_object(wood)
    tree_id = wood[TREE_ID_KEY]
    tree_collection = _find_tree_collection(tree_id)
    if tree_collection is None:
        raise ValueError("Selected tree has no owning collection")

    template_objects, _ = ensure_canopy_templates()
    templates = {template.name: template for template in template_objects}
    anchors = _extract_branch_anchors(wood)
    placements = build_lobe_layout(
        anchors,
        count=int(wood.mtree_lobe_count),
        scale_multiplier=float(wood.mtree_lobe_scale),
        seed=int(wood.mtree_canopy_seed),
    )
    new_mesh = _build_foliage_mesh(templates, placements)
    foliage = bpy.data.objects.new(f"{tree_collection.name}_Foliage_New", new_mesh)
    tree_collection.objects.link(foliage)
    foliage.parent = wood.parent
    foliage.matrix_local = wood.matrix_local.copy()
    foliage[ROLE_KEY] = ROLE_FOLIAGE
    foliage[TREE_ID_KEY] = tree_id
    foliage[SEED_KEY] = int(wood.mtree_canopy_seed)
    if wood.get(TREE_SPECIES_KEY):
        foliage[TREE_SPECIES_KEY] = wood[TREE_SPECIES_KEY]
        foliage[TREE_NUMBER_KEY] = int(wood[TREE_NUMBER_KEY])
    foliage["mtree_lobe_count"] = len(placements)

    old_foliage = [
        obj
        for obj in list(tree_collection.objects)
        if obj != foliage and obj.get(ROLE_KEY) == ROLE_FOLIAGE
    ]
    for old in old_foliage:
        old_mesh = old.data if old.type == "MESH" else None
        bpy.data.objects.remove(old, do_unlink=True)
        if old_mesh is not None and old_mesh.users == 0:
            bpy.data.meshes.remove(old_mesh)
    foliage.name = f"{tree_collection.name}_Foliage"
    new_mesh.name = foliage.name
    return foliage, len(placements)


def register_properties() -> None:
    bpy.types.Object.mtree_lobe_count = bpy.props.IntProperty(
        name="Lobe Count",
        description="Number of canopy lobes generated for this tree",
        default=8,
        min=1,
        max=32,
    )
    bpy.types.Object.mtree_lobe_scale = bpy.props.FloatProperty(
        name="Lobe Scale",
        description="Multiplier over the automatically calculated canopy lobe size",
        default=1.0,
        min=0.1,
        max=4.0,
    )
    bpy.types.Object.mtree_canopy_seed = bpy.props.IntProperty(
        name="Canopy Seed",
        description="Deterministic seed for canopy placement and variation",
        default=0,
        min=0,
    )


def unregister_properties() -> None:
    for name in ("mtree_canopy_seed", "mtree_lobe_scale", "mtree_lobe_count"):
        if hasattr(bpy.types.Object, name):
            delattr(bpy.types.Object, name)
