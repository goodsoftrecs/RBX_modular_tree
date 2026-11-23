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
    TREE_NUMBER_KEY,
    TREE_SPECIES_KEY,
    find_wood_for_object,
    layout_generated_tree_gallery,
    organize_tree_object,
)
from .foliage_anchor_data import (
    FoliageAnchor,
    load_anchor_payload,
    load_retained_branch_ids,
)
from .foliage_card_layout import (
    CardPlacement,
    build_card_layout,
    rotate_card_layout_about_z,
    rotate_uv_within_bounds,
)


FOLIAGE_LIBRARY_NAME = "MTree_FoliageLibrary"
ROLE_FOLIAGE_TEMPLATE = "FOLIAGE_CARD_TEMPLATE"
ROLE_FOLIAGE_SET = "FOLIAGE_CARD_SET"
ROLE_FOLIAGE_SET_LABEL = "FOLIAGE_CARD_SET_LABEL"
FOLIAGE_SET_KEY = "mtree_foliage_set_id"
FOLIAGE_SLOT_KEY = "mtree_foliage_slot"
GENERATED_MATERIAL_KEY = "mtree_generated_foliage_material"
BRANCH_LAYERS_SECONDARY = "SECONDARY_ONLY"
BRANCH_LAYERS_PRIMARY_SECONDARY = "PRIMARY_SECONDARY"
CONIFER_PRIMARY_SPECIES = frozenset({"PINE", "CEDAR", "SEQUOIA", "HEMLOCK"})
BRANCH_LAYER_ITEMS = (
    (
        BRANCH_LAYERS_SECONDARY,
        "Secondary Only",
        "Start foliage cards where secondary branches connect",
    ),
    (
        BRANCH_LAYERS_PRIMARY_SECONDARY,
        "Primary + Secondary",
        "Also start long foliage cards where primary branches meet the trunk",
    ),
)

FOLIAGE_SET_ITEMS = (
    ("OAK", "Oak", "Oak foliage atlas set"),
    ("BIRCH", "Birch", "Birch foliage atlas set"),
    ("PINE", "Pine", "Pine foliage atlas set"),
    ("CEDAR", "Cedar", "Cedar foliage atlas set"),
    ("WALNUT", "Walnut", "Walnut foliage atlas set"),
    ("SEQUOIA", "Sequoia", "Sequoia foliage atlas set"),
    ("HEMLOCK", "Hemlock", "Hemlock foliage atlas set"),
    ("TEAK", "Teak", "Teak foliage atlas set"),
)
TREE_FOLIAGE_SET_ITEMS = (
    ("NONE", "None", "No foliage atlas set selected"),
    *FOLIAGE_SET_ITEMS,
)
FOLIAGE_SLOT_SPECS = (
    (1, "Large_A", (0.0, 0.5, 0.5, 1.0)),
    (2, "Large_B", (0.5, 0.5, 1.0, 1.0)),
    (3, "Small_A", (0.0, 0.0, 0.5, 0.5)),
    (4, "Small_B", (0.5, 0.0, 1.0, 0.5)),
)

_SET_LABELS = {identifier: label for identifier, label, _ in FOLIAGE_SET_ITEMS}
_SLOT_BOUNDS = {slot: bounds for slot, _, bounds in FOLIAGE_SLOT_SPECS}
_SLOT_OFFSETS = {slot: (-3.0 + (slot - 1) * 2.0, 0.0, 0.0) for slot in range(1, 5)}


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


def _preview_material(set_id: str) -> bpy.types.Material:
    label = _SET_LABELS[set_id]
    material_name = f"MTree_{label}_FoliageAtlas"
    material = bpy.data.materials.get(material_name)
    if material is None:
        material = bpy.data.materials.new(material_name)
        material.diffuse_color = (0.12, 0.48, 0.08, 1.0)
        material.roughness = 0.82
        material.use_nodes = True
        principled = material.node_tree.nodes.get("Principled BSDF")
        if principled is not None:
            principled.inputs["Base Color"].default_value = (0.12, 0.48, 0.08, 1.0)
            principled.inputs["Roughness"].default_value = 0.82
    return material


def _create_template_mesh(
    name: str,
    uv_bounds: tuple[float, float, float, float],
    material: bpy.types.Material,
) -> bpy.types.Mesh:
    """Create a unit card in local X/Z; +Z is the branch-following long axis."""

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(
        [(-0.5, 0.0, 0.0), (0.5, 0.0, 0.0), (0.5, 0.0, 1.0), (-0.5, 0.0, 1.0)],
        [],
        [(0, 1, 2, 3)],
    )
    mesh.update(calc_edges=True)
    uv_layer = mesh.uv_layers.new(name="UVMap")
    minimum_u, minimum_v, maximum_u, maximum_v = uv_bounds
    for loop_index, uv in enumerate(
        (
            (minimum_u, minimum_v),
            (maximum_u, minimum_v),
            (maximum_u, maximum_v),
            (minimum_u, maximum_v),
        )
    ):
        uv_layer.data[loop_index].uv = uv
    mesh.materials.append(material)
    return mesh


def _validate_set_id(set_id: str) -> str:
    normalized = str(set_id).upper()
    if normalized not in _SET_LABELS:
        raise ValueError(f"Unsupported foliage set: {set_id}")
    return normalized


def _find_set_collection(set_id: str) -> bpy.types.Collection | None:
    library = bpy.data.collections.get(FOLIAGE_LIBRARY_NAME)
    if library is None:
        return None
    matches = [
        collection
        for collection in library.children
        if collection.get(ROLE_KEY) == ROLE_FOLIAGE_SET
        and collection.get(FOLIAGE_SET_KEY) == set_id
    ]
    if len(matches) > 1:
        raise ValueError(f"Foliage set '{set_id}' has multiple source collections")
    return matches[0] if matches else None


def foliage_set_exists(set_id: str) -> bool:
    return _find_set_collection(_validate_set_id(set_id)) is not None


def default_tree_foliage_set_id(preset: str, selected_set_id: str) -> str:
    """Resolve a newly generated tree's set without silently creating library data."""

    candidate = selected_set_id if preset == "RANDOM" else preset
    if candidate in _SET_LABELS and foliage_set_exists(candidate):
        return candidate
    return "NONE"


def default_foliage_branch_layers(species_id: str | None) -> str:
    """Return the authored species default without removing per-tree overrides."""

    return (
        BRANCH_LAYERS_PRIMARY_SECONDARY
        if str(species_id or "").upper() in CONIFER_PRIMARY_SPECIES
        else BRANCH_LAYERS_SECONDARY
    )


def default_foliage_top_tip_pairs(species_id: str | None) -> int:
    """Return one terminal leader pair for conifers and none for broadleaf trees."""

    return 1 if str(species_id or "").upper() in CONIFER_PRIMARY_SPECIES else 0


def ensure_foliage_branch_layers_default(wood: bpy.types.Object) -> str:
    """Migrate an existing tree only when the artist has never set the control."""

    property_name = "mtree_foliage_branch_layers"
    if not wood.is_property_set(property_name):
        wood.mtree_foliage_branch_layers = default_foliage_branch_layers(
            wood.get(TREE_SPECIES_KEY)
        )
    return str(wood.mtree_foliage_branch_layers)


def ensure_foliage_top_tip_pairs_default(wood: bpy.types.Object) -> int:
    """Migrate an existing tree only when the artist has never set the control."""

    property_name = "mtree_foliage_top_tip_pairs"
    if not wood.is_property_set(property_name):
        wood.mtree_foliage_top_tip_pairs = default_foliage_top_tip_pairs(
            wood.get(TREE_SPECIES_KEY)
        )
    return int(wood.mtree_foliage_top_tip_pairs)


def _set_id_from_context(context: bpy.types.Context) -> str:
    active = context.active_object
    if active is not None and active.get(ROLE_KEY) in {
        ROLE_FOLIAGE_TEMPLATE,
        ROLE_FOLIAGE_SET_LABEL,
    }:
        value = active.get(FOLIAGE_SET_KEY)
        if value:
            return _validate_set_id(value)
    active_collection = getattr(context, "collection", None)
    if (
        active_collection is not None
        and active_collection.get(ROLE_KEY) == ROLE_FOLIAGE_SET
    ):
        value = active_collection.get(FOLIAGE_SET_KEY)
        if value:
            return _validate_set_id(value)
    return _validate_set_id(context.scene.mtree_foliage_library_set_id)


def _validate_template(template: bpy.types.Object, slot: int) -> bpy.types.Material:
    if template.type != "MESH":
        raise ValueError(f"Foliage slot {slot} must be a mesh object")
    if len(template.data.vertices) < 3 or len(template.data.polygons) < 1:
        raise ValueError(f"Foliage slot {slot} must contain mesh geometry")
    uv_layer = template.data.uv_layers.active
    if uv_layer is None:
        raise ValueError(f"Foliage slot {slot} must contain an active UV map")
    if len(template.data.materials) != 1 or template.data.materials[0] is None:
        raise ValueError(f"Foliage slot {slot} must use exactly one material")
    minimum_u, minimum_v, maximum_u, maximum_v = _SLOT_BOUNDS[slot]
    for loop in uv_layer.data:
        u, v = loop.uv
        if not (
            minimum_u - 1e-6 <= u <= maximum_u + 1e-6
            and minimum_v - 1e-6 <= v <= maximum_v + 1e-6
        ):
            raise ValueError(f"Foliage slot {slot} has UVs outside its atlas quadrant")
    return template.data.materials[0]


def _existing_templates(collection: bpy.types.Collection) -> dict[int, bpy.types.Object]:
    templates: dict[int, bpy.types.Object] = {}
    set_id = collection.get(FOLIAGE_SET_KEY)
    for obj in collection.objects:
        if obj.get(ROLE_KEY) != ROLE_FOLIAGE_TEMPLATE:
            continue
        if obj.get(FOLIAGE_SET_KEY) != set_id:
            raise ValueError(f"Foliage template '{obj.name}' has mismatched set metadata")
        slot = int(obj.get(FOLIAGE_SLOT_KEY, 0))
        if slot not in _SLOT_BOUNDS:
            raise ValueError(f"Foliage template '{obj.name}' has an invalid slot")
        if slot in templates:
            raise ValueError(f"Foliage set has more than one template for slot {slot}")
        templates[slot] = obj
    return templates


def _row_origin(set_id: str) -> Vector:
    row_index = tuple(_SET_LABELS).index(set_id)
    return Vector((0.0, -15.0, 1.0 - row_index * 3.0))


def _ensure_set_label(
    collection: bpy.types.Collection, set_id: str, origin: Vector
) -> bpy.types.Object:
    labels = [
        obj
        for obj in collection.objects
        if obj.get(ROLE_KEY) == ROLE_FOLIAGE_SET_LABEL
    ]
    if len(labels) > 1:
        raise ValueError(f"Foliage set '{set_id}' has multiple labels")
    if labels:
        return labels[0]
    curve = bpy.data.curves.new(f"{_SET_LABELS[set_id]}_Foliage_Label", "FONT")
    curve.body = f"{_SET_LABELS[set_id]} Foliage"
    curve.align_x = "LEFT"
    curve.size = 0.55
    label = bpy.data.objects.new(curve.name, curve)
    collection.objects.link(label)
    label.location = origin + Vector((-4.2, 0.0, 1.45))
    label.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    label[ROLE_KEY] = ROLE_FOLIAGE_SET_LABEL
    label[FOLIAGE_SET_KEY] = set_id
    return label


def ensure_foliage_card_set(
    context: bpy.types.Context | None = None, set_id: str | None = None
) -> tuple[bpy.types.Collection, list[bpy.types.Object], int]:
    """Initialize or repair one four-slot species set without replacing valid slots."""

    context = context or bpy.context
    resolved_set_id = _validate_set_id(set_id) if set_id else _set_id_from_context(context)
    library = _get_or_create_library()
    collection = _find_set_collection(resolved_set_id)
    if collection is None:
        collection = bpy.data.collections.new(
            f"MTree_Foliage_{_SET_LABELS[resolved_set_id]}"
        )
        library.children.link(collection)
        collection[ROLE_KEY] = ROLE_FOLIAGE_SET
        collection[FOLIAGE_SET_KEY] = resolved_set_id

    templates = _existing_templates(collection)
    materials = [
        _validate_template(template, slot) for slot, template in templates.items()
    ]
    if materials and any(material != materials[0] for material in materials[1:]):
        raise ValueError(
            f"{_SET_LABELS[resolved_set_id]} foliage slots must share one atlas material"
        )
    material = materials[0] if materials else _preview_material(resolved_set_id)

    if templates:
        reference_slot = min(templates)
        reference_offset = Vector(_SLOT_OFFSETS[reference_slot])
        origin = templates[reference_slot].location - reference_offset
    else:
        origin = _row_origin(resolved_set_id)

    created = 0
    for slot, slot_name, bounds in FOLIAGE_SLOT_SPECS:
        if slot in templates:
            continue
        object_name = f"{_SET_LABELS[resolved_set_id]}_Foliage_{slot_name}"
        mesh = _create_template_mesh(object_name, bounds, material)
        template = bpy.data.objects.new(object_name, mesh)
        collection.objects.link(template)
        template.location = origin + Vector(_SLOT_OFFSETS[slot])
        template[ROLE_KEY] = ROLE_FOLIAGE_TEMPLATE
        template[FOLIAGE_SET_KEY] = resolved_set_id
        template[FOLIAGE_SLOT_KEY] = slot
        templates[slot] = template
        created += 1

    ordered = [templates[slot] for slot in range(1, 5)]
    shared_materials = [
        _validate_template(template, slot)
        for slot, template in enumerate(ordered, 1)
    ]
    if any(material != shared_materials[0] for material in shared_materials[1:]):
        raise ValueError(
            f"{_SET_LABELS[resolved_set_id]} foliage slots must share one atlas material"
        )
    _ensure_set_label(collection, resolved_set_id, origin)
    return collection, ordered, created


def resolve_foliage_templates(set_id: str) -> list[bpy.types.Object]:
    resolved_set_id = _validate_set_id(set_id)
    collection = _find_set_collection(resolved_set_id)
    if collection is None:
        raise ValueError(
            f"Foliage set '{_SET_LABELS[resolved_set_id]}' is not initialized"
        )
    templates = _existing_templates(collection)
    missing = [str(slot) for slot in range(1, 5) if slot not in templates]
    if missing:
        raise ValueError(f"Foliage set is missing atlas slots: {', '.join(missing)}")
    ordered = [templates[slot] for slot in range(1, 5)]
    materials = [
        _validate_template(template, slot)
        for slot, template in enumerate(ordered, 1)
    ]
    if any(material != materials[0] for material in materials[1:]):
        raise ValueError("All four foliage slots must share exactly one atlas material")
    return ordered


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


def _missing_branch_ids_for_wood(
    wood: bpy.types.Object, anchors: list[FoliageAnchor]
) -> frozenset[int]:
    """Return complete-graph branches omitted by the authoritative native mesher."""

    retained_branch_ids = load_retained_branch_ids(wood, anchors)
    non_trunk_branch_ids = {
        anchor.branch_id for anchor in anchors if anchor.hierarchy_depth > 0
    }
    return frozenset(non_trunk_branch_ids - retained_branch_ids)


def _template_local_matrix(template: bpy.types.Object) -> Matrix:
    return template.rotation_euler.to_matrix().to_4x4() @ Matrix.Diagonal(
        (template.scale.x, template.scale.y, template.scale.z, 1.0)
    )


def _template_footprint(templates: list[bpy.types.Object]) -> float:
    """Return the largest authored card diagonal before generated placement scale."""

    footprint = 0.0
    for template in templates:
        template_matrix = _template_local_matrix(template)
        vertices = [template_matrix @ vertex.co for vertex in template.data.vertices]
        for index, first in enumerate(vertices):
            for second in vertices[:index]:
                footprint = max(footprint, (first - second).length)
    if not math.isfinite(footprint) or footprint <= 1e-8:
        raise ValueError("Foliage templates must have a non-zero finite footprint")
    return footprint


def _axis_basis(long_axis: Vector, normal: Vector) -> Matrix:
    """Build a right-handed card basis with columns width, normal, and long."""

    long_axis = long_axis.normalized()
    normal = normal.normalized()
    width_axis = normal.cross(long_axis)
    if width_axis.length <= 1e-8:
        raise ValueError("Foliage card direction and normal must not be parallel")
    width_axis.normalize()
    normal = long_axis.cross(width_axis).normalized()
    return Matrix(
        (
            (width_axis.x, normal.x, long_axis.x, 0.0),
            (width_axis.y, normal.y, long_axis.y, 0.0),
            (width_axis.z, normal.z, long_axis.z, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )
    )


def _template_attachment_frame(
    template: bpy.types.Object,
    uv_bounds: tuple[float, float, float, float],
) -> tuple[Vector, Vector, Vector]:
    """Return authored attachment, attachment-to-center axis, and plane normal."""

    source_mesh = template.data
    source_uv = source_mesh.uv_layers.active
    if source_uv is None:
        raise ValueError("Foliage card template must contain an active UV map")

    maximum_u, maximum_v = uv_bounds[2], uv_bounds[3]
    corner_vertex_indices = {
        source_mesh.loops[loop_index].vertex_index
        for loop_index, loop in enumerate(source_uv.data)
        if abs(float(loop.uv.x) - maximum_u) <= 1e-5
        and abs(float(loop.uv.y) - maximum_v) <= 1e-5
    }
    if not corner_vertex_indices:
        slot = int(template.get(FOLIAGE_SLOT_KEY, 0))
        raise ValueError(
            f"Foliage template slot {slot} must contain its exact top-right UV corner"
        )
    if not source_mesh.vertices:
        raise ValueError("Foliage card template must contain mesh vertices")

    template_matrix = _template_local_matrix(template)
    authored_vertices = [template_matrix @ vertex.co for vertex in source_mesh.vertices]
    attachment = sum(
        (authored_vertices[index] for index in corner_vertex_indices), Vector()
    ) / len(corner_vertex_indices)
    center = sum(authored_vertices, Vector()) / len(authored_vertices)

    plane_normal = None
    for polygon in source_mesh.polygons:
        polygon_indices = list(polygon.vertices)
        if len(polygon_indices) < 3:
            continue
        first = authored_vertices[polygon_indices[0]]
        for index in range(1, len(polygon_indices) - 1):
            edge_a = authored_vertices[polygon_indices[index]] - first
            edge_b = authored_vertices[polygon_indices[index + 1]] - first
            candidate = edge_a.cross(edge_b)
            if candidate.length > 1e-8:
                plane_normal = candidate.normalized()
                break
        if plane_normal is not None:
            break
    if plane_normal is None:
        raise ValueError("Foliage card template must contain a non-degenerate face")

    long_axis = center - attachment
    long_axis -= plane_normal * long_axis.dot(plane_normal)
    if long_axis.length <= 1e-8:
        raise ValueError(
            "Foliage card center must differ from its top-right attachment corner"
        )
    return attachment, long_axis.normalized(), plane_normal


def _card_transform(
    template: bpy.types.Object,
    placement: CardPlacement,
    uv_bounds: tuple[float, float, float, float],
    branch_distance: float,
) -> Matrix:
    """Map an authored top-right UV corner onto one generated branch anchor."""

    if not math.isfinite(branch_distance):
        raise ValueError("Branch Distance must be finite")
    attachment, source_long, source_normal = _template_attachment_frame(
        template, uv_bounds
    )
    target_long = Vector(placement.direction).normalized()
    target_normal = Vector(placement.normal).normalized()
    target_position = Vector(placement.position) + target_normal * branch_distance
    return (
        Matrix.Translation(target_position)
        @ _axis_basis(target_long, target_normal)
        @ Matrix.Diagonal(
            (
                placement.scale,
                placement.scale,
                placement.scale * placement.length_scale,
                1.0,
            )
        )
        @ _axis_basis(source_long, source_normal).inverted()
        @ Matrix.Translation(-attachment)
        @ _template_local_matrix(template)
    )


def _build_foliage_mesh(
    templates: list[bpy.types.Object],
    placements: list[CardPlacement],
    texture_rotation_radians: float = 0.0,
    output_material: bpy.types.Material | None = None,
    branch_distance: float = 0.0,
) -> bpy.types.Mesh:
    if len(templates) != 4:
        raise ValueError("Foliage generation requires all four atlas templates")

    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    face_uvs: list[list[tuple[float, float]]] = []

    for placement in placements:
        if placement.template_slot not in _SLOT_BOUNDS:
            raise ValueError(f"Invalid foliage template slot: {placement.template_slot}")
        template = templates[placement.template_slot - 1]
        source_mesh = template.data
        source_uv = source_mesh.uv_layers.active
        if source_uv is None:
            raise ValueError("Foliage card template must contain an active UV map")
        transform = _card_transform(
            template,
            placement,
            _SLOT_BOUNDS[placement.template_slot],
            branch_distance,
        )
        vertex_offset = len(vertices)
        vertices.extend(tuple(transform @ vertex.co) for vertex in source_mesh.vertices)
        for polygon in source_mesh.polygons:
            faces.append(tuple(vertex_offset + index for index in polygon.vertices))
            face_uvs.append(
                [
                    rotate_uv_within_bounds(
                        tuple(source_uv.data[index].uv),
                        texture_rotation_radians,
                        _SLOT_BOUNDS[placement.template_slot],
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
    mesh.materials.append(output_material or templates[0].data.materials[0])
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

    set_id = str(wood.mtree_foliage_set_id)
    if set_id == "NONE":
        raise ValueError("Select an initialized foliage atlas set for this tree")
    templates = resolve_foliage_templates(set_id)
    anchors = load_anchor_payload(wood)
    missing_branch_ids = _missing_branch_ids_for_wood(wood, anchors)
    branch_layers = ensure_foliage_branch_layers_default(wood)
    top_tip_pairs = ensure_foliage_top_tip_pairs_default(wood)
    placements = build_card_layout(
        anchors,
        cluster_count=int(wood.mtree_foliage_cluster_count),
        scale_multiplier=float(wood.mtree_foliage_card_scale),
        seed=int(wood.mtree_foliage_seed),
        pair_rotation_radians=float(wood.mtree_foliage_pair_rotation),
        template_slots=(1, 2, 3, 4),
        missing_branch_ids=missing_branch_ids,
        branch_spacing=float(wood.mtree_foliage_branch_spacing),
        template_footprint=_template_footprint(templates),
        branch_card_length=float(wood.mtree_foliage_branch_card_length),
        primary_card_length=float(wood.mtree_foliage_primary_card_length),
        length_variation=float(wood.mtree_foliage_length_variation) * 0.01,
        include_primary_connections=(
            branch_layers == BRANCH_LAYERS_PRIMARY_SECONDARY
        ),
        top_tip_pairs=top_tip_pairs,
    )
    placements = rotate_card_layout_about_z(
        placements, float(wood.mtree_foliage_canopy_rotation)
    )
    texture_rotation = float(wood.mtree_foliage_texture_rotation)
    generated_material = _material_for_texture_rotation(
        templates[0].data.materials[0], texture_rotation, tree_collection.name
    )
    try:
        new_mesh = _build_foliage_mesh(
            templates,
            placements,
            texture_rotation_radians=texture_rotation,
            output_material=generated_material,
            branch_distance=float(wood.mtree_foliage_branch_distance),
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
    if wood.get(TREE_SPECIES_KEY):
        foliage[TREE_SPECIES_KEY] = wood[TREE_SPECIES_KEY]
        foliage[TREE_NUMBER_KEY] = int(wood[TREE_NUMBER_KEY])
    foliage[FOLIAGE_SET_KEY] = set_id
    foliage["mtree_foliage_cluster_count"] = int(wood.mtree_foliage_cluster_count)
    foliage["mtree_foliage_card_count"] = len(placements)
    foliage["mtree_foliage_branch_distance"] = float(
        wood.mtree_foliage_branch_distance
    )
    foliage["mtree_foliage_branch_spacing"] = float(
        wood.mtree_foliage_branch_spacing
    )
    foliage["mtree_foliage_branch_card_length"] = float(
        wood.mtree_foliage_branch_card_length
    )
    foliage["mtree_foliage_primary_card_length"] = float(
        wood.mtree_foliage_primary_card_length
    )
    foliage["mtree_foliage_branch_layers"] = branch_layers
    foliage["mtree_foliage_top_tip_pairs"] = top_tip_pairs
    foliage["mtree_foliage_top_tip_clusters"] = sum(
        placements[index].is_top_tip for index in range(0, len(placements), 2)
    )
    foliage["mtree_foliage_length_variation"] = float(
        wood.mtree_foliage_length_variation
    )
    foliage["mtree_foliage_variant_slots"] = [
        placements[index].template_slot for index in range(0, len(placements), 2)
    ]
    missing_cluster_count = sum(
        anchors[placements[index].anchor_index].branch_id in missing_branch_ids
        for index in range(0, len(placements), 2)
    )
    foliage["mtree_foliage_missing_branch_count"] = len(missing_branch_ids)
    foliage["mtree_foliage_missing_branch_clusters"] = missing_cluster_count
    foliage["mtree_foliage_physical_branch_clusters"] = (
        int(wood.mtree_foliage_cluster_count) - missing_cluster_count
    )
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
    layout_generated_tree_gallery()
    return foliage, int(wood.mtree_foliage_cluster_count), len(placements)


def register_properties() -> None:
    bpy.types.Scene.mtree_foliage_library_set_id = bpy.props.EnumProperty(
        name="Foliage Set",
        description="Species atlas set to initialize or repair",
        items=FOLIAGE_SET_ITEMS,
        default="OAK",
    )
    bpy.types.Object.mtree_foliage_set_id = bpy.props.EnumProperty(
        name="Tree Foliage Set",
        description="Four-variant atlas set used when generating this tree's foliage",
        items=TREE_FOLIAGE_SET_ITEMS,
        default="NONE",
    )
    bpy.types.Object.mtree_foliage_cluster_count = bpy.props.IntProperty(
        name="Foliage Cluster Count",
        description="Exact number of shallow-V foliage card pairs",
        default=30,
        min=1,
        max=512,
    )
    bpy.types.Object.mtree_foliage_top_tip_pairs = bpy.props.IntProperty(
        name="Top Tip Pairs",
        description=(
            "Foliage pairs reserved inside the exact cluster count at the terminal trunk tip"
        ),
        default=0,
        min=0,
        max=2,
    )
    bpy.types.Object.mtree_foliage_card_scale = bpy.props.FloatProperty(
        name="Card Scale",
        description="Multiplier over the automatically derived foliage card size",
        default=1.0,
        min=0.1,
        max=12.0,
    )
    bpy.types.Object.mtree_foliage_branch_spacing = bpy.props.FloatProperty(
        name="Branch Spacing",
        description=(
            "Longitudinal cluster spacing relative to the generated foliage card footprint"
        ),
        default=1.0,
        min=0.1,
        max=3.0,
    )
    bpy.types.Object.mtree_foliage_branch_card_length = bpy.props.FloatProperty(
        name="Branch Card Length",
        description="Longitudinal card multiplier; width remains controlled by Card Scale",
        default=1.5,
        min=0.5,
        max=3.0,
    )
    bpy.types.Object.mtree_foliage_primary_card_length = bpy.props.FloatProperty(
        name="Primary Card Length",
        description="Longitudinal multiplier for cards beginning at trunk connections",
        default=2.0,
        min=0.5,
        max=4.0,
    )
    bpy.types.Object.mtree_foliage_branch_layers = bpy.props.EnumProperty(
        name="Branch Start Layers",
        description="Choose which branch connection depths receive starting cards",
        items=BRANCH_LAYER_ITEMS,
        default=BRANCH_LAYERS_SECONDARY,
    )
    bpy.types.Object.mtree_foliage_length_variation = bpy.props.FloatProperty(
        name="Length Variation",
        description=(
            "Deterministic per-cluster variation around Branch Card Length; zero is off"
        ),
        subtype="PERCENTAGE",
        default=0.0,
        min=0.0,
        max=50.0,
    )
    bpy.types.Object.mtree_foliage_branch_distance = bpy.props.FloatProperty(
        name="Branch Distance",
        description=(
            "Signed perpendicular distance from the branch to each card's top-right "
            "attachment corner; positive moves outward and negative moves inward"
        ),
        default=0.0,
        min=-12.0,
        max=12.0,
    )
    bpy.types.Object.mtree_foliage_texture_rotation = bpy.props.FloatProperty(
        name="Texture Rotation",
        description="Rotate each card's UVs while keeping them inside its atlas quadrant",
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
        "mtree_foliage_branch_distance",
        "mtree_foliage_length_variation",
        "mtree_foliage_branch_layers",
        "mtree_foliage_primary_card_length",
        "mtree_foliage_branch_card_length",
        "mtree_foliage_branch_spacing",
        "mtree_foliage_card_scale",
        "mtree_foliage_top_tip_pairs",
        "mtree_foliage_cluster_count",
        "mtree_foliage_set_id",
    ):
        if hasattr(bpy.types.Object, name):
            delattr(bpy.types.Object, name)
    if hasattr(bpy.types.Scene, "mtree_foliage_library_set_id"):
        del bpy.types.Scene.mtree_foliage_library_set_id
