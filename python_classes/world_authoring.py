"""In-place RBX World Authoring contract for generated MTree collections."""

from __future__ import annotations

import re

import bpy


PREFAB_LIBRARY_NAME = "RBX_PrefabLibrary_Placements"
LEGACY_PREFAB_LIBRARY_NAME = "RBX_PrefabLibrary"
GROUND_ANCHOR_NAME = "RBX_GroundAnchor_Att"
LEGACY_GROUND_ANCHOR_NAME = "RBX_GroundAnchor"
GROUND_ANCHOR_ROLE_KEY = "rbx_ground_anchor"
PREFAB_SCHEMA_VERSION = 1

PREFAB_DEFAULTS = {
    "rbx_enabled": False,
    "rbx_prefab_key": None,
    "rbx_category": "tree",
    "rbx_weight": 1.0,
    "rbx_alignment": "upright",
    "rbx_scale_min": 1.0,
    "rbx_scale_max": 1.0,
    "rbx_slope_max_deg": 30.0,
    "rbx_spacing_radius": 8.0,
    "rbx_biomes": "",
    "rbx_schema_version": PREFAB_SCHEMA_VERSION,
}


def _normalize_prefab_key(collection_name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(collection_name).lower()).strip("_")
    if not normalized:
        raise ValueError("Tree collection name cannot produce a non-empty RBX prefab key")
    return normalized


def _ensure_prefab_library() -> bpy.types.Collection:
    canonical = bpy.data.collections.get(PREFAB_LIBRARY_NAME)
    legacy = bpy.data.collections.get(LEGACY_PREFAB_LIBRARY_NAME)
    if canonical is not None and legacy is not None and canonical != legacy:
        raise ValueError(
            "Both RBX_PrefabLibrary_Placements and legacy RBX_PrefabLibrary exist; "
            "resolve the duplicate libraries before generating trees"
        )
    if canonical is None and legacy is not None:
        legacy.name = PREFAB_LIBRARY_NAME
        canonical = legacy
    if canonical is None:
        canonical = bpy.data.collections.new(PREFAB_LIBRARY_NAME)
    scene_children = bpy.context.scene.collection.children
    if canonical not in list(scene_children):
        scene_children.link(canonical)
    return canonical


def _ground_anchor_number(name: str) -> int | None:
    if name in {GROUND_ANCHOR_NAME, LEGACY_GROUND_ANCHOR_NAME}:
        return 0
    match = re.fullmatch(r"RBX_GroundAnchor\.(\d+)_Att", name)
    if match:
        return int(match.group(1))
    match = re.fullmatch(r"RBX_GroundAnchor(?:_Att)?\.(\d+)", name)
    if match:
        return int(match.group(1))
    return None


def _canonical_ground_anchor_name(number: int) -> str:
    if number == 0:
        return GROUND_ANCHOR_NAME
    return f"{LEGACY_GROUND_ANCHOR_NAME}.{number:03d}_Att"


def _is_ground_anchor(obj: bpy.types.Object) -> bool:
    return bool(
        obj.type in {"EMPTY", "MESH"}
        and (
            obj.get(GROUND_ANCHOR_ROLE_KEY) is True
            or _ground_anchor_number(obj.name) is not None
        )
    )


def _assign_canonical_ground_anchor_name(anchor: bpy.types.Object) -> None:
    current_number = _ground_anchor_number(anchor.name)
    candidate_numbers = [] if current_number is None else [current_number]
    candidate_numbers.extend(number for number in range(10000) if number != current_number)
    for number in candidate_numbers:
        candidate = _canonical_ground_anchor_name(number)
        existing = bpy.data.objects.get(candidate)
        if existing is None or existing is anchor:
            anchor.name = candidate
            return
    raise ValueError("Could not assign a unique RBX ground-anchor attachment name")


def _ensure_ground_anchor(
    tree_collection: bpy.types.Collection, root: bpy.types.Object
) -> bpy.types.Object:
    anchors = [obj for obj in tree_collection.objects if _is_ground_anchor(obj)]
    if len(anchors) > 1:
        raise ValueError(f"{tree_collection.name} has multiple RBX ground anchors")
    if anchors:
        anchor = anchors[0]
        original_world = anchor.matrix_world.copy()
        if anchor.parent is None:
            anchor.parent = root
            anchor.matrix_world = original_world
    else:
        anchor = bpy.data.objects.new(GROUND_ANCHOR_NAME, None)
        tree_collection.objects.link(anchor)
        anchor.parent = root
        anchor.location = (0.0, 0.0, 0.0)
        anchor.empty_display_type = "PLAIN_AXES"
        anchor.empty_display_size = 0.25
    _assign_canonical_ground_anchor_name(anchor)
    anchor[GROUND_ANCHOR_ROLE_KEY] = True
    anchor["rbx_anchor_role"] = "ground"
    return anchor


def ensure_tree_prefab(
    tree_collection: bpy.types.Collection, root: bpy.types.Object
) -> bpy.types.Object:
    """Repair one generated tree and link its collection into the RBX prefab library."""

    if root.name not in tree_collection.objects:
        raise ValueError(f"{root.name} must be directly linked to {tree_collection.name}")
    for property_name, configured_default in PREFAB_DEFAULTS.items():
        if property_name in tree_collection:
            continue
        default = configured_default
        if property_name == "rbx_prefab_key":
            default = _normalize_prefab_key(tree_collection.name)
        tree_collection[property_name] = default

    anchor = _ensure_ground_anchor(tree_collection, root)
    library = _ensure_prefab_library()
    if tree_collection not in list(library.children):
        library.children.link(tree_collection)
    return anchor
