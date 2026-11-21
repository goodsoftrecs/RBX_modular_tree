"""Blender operators for MTree addon."""

from __future__ import annotations

import time
from random import randint

import bpy
from bpy.utils import register_class, unregister_class

from .canopy_lobes import (
    ensure_canopy_templates,
    organize_tree_object,
    refresh_canopy_for_object,
)
from .foliage_anchor_data import (
    anchors_from_native,
    store_anchor_payload,
    store_retained_branch_ids,
)
from .foliage_cards import (
    default_foliage_branch_layers,
    default_tree_foliage_set_id,
    ensure_foliage_card_set,
    refresh_foliage_cards_for_object,
)
from .m_tree_wrapper import lazy_m_tree as m_tree
from .mesh_utils import create_mesh_from_cpp
from .game_output_profiles import (
    ROBLOX_GAME_BUDGET,
    WOOD_OUTPUT_PROFILE_ITEMS,
    resolve_wood_mesher_settings,
)
from .pivot_painter import ExportFormat, PivotPainterExporter
from .presets import (
    TREE_PRESETS,
    apply_preset,
    apply_preset_to_generator,
    apply_sub_branch_preset,
    apply_trunk_preset,
    get_growth_preset_items,
    get_preset_items,
)
from .presets.leaf_presets import LEAF_PRESETS, get_leaf_preset_items
from .resources.node_groups import distribute_leaves
from .quick_generate_settings import reset_generation_overrides


class ExecuteNodeFunction(bpy.types.Operator):
    """Execute a function on a node by name."""

    bl_idname = "mtree.node_function"
    bl_label = "Node Function callback"
    bl_options = {"REGISTER", "UNDO"}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()
    function_name: bpy.props.StringProperty()

    def execute(self, context):
        node = bpy.data.node_groups[self.node_tree_name].nodes[self.node_name]
        getattr(node, self.function_name)()
        return {"FINISHED"}


class AddLeavesModifier(bpy.types.Operator):
    """Add leaves distribution modifier to tree."""

    bl_idname = "mtree.add_leaves"
    bl_label = "Add leaves distribution modifier to tree"
    bl_options = {"REGISTER", "UNDO"}

    object_id: bpy.props.StringProperty()
    distribution_mode: bpy.props.IntProperty(
        name="Distribution Mode",
        description="0=Random, 1=Phyllotactic",
        default=0,
        min=0,
        max=1,
    )
    phyllotaxis_angle: bpy.props.FloatProperty(
        name="Phyllotaxis Angle",
        description="Divergence angle in degrees (137.5 = golden angle)",
        default=137.5,
        min=0.0,
        max=360.0,
    )
    billboard_mode: bpy.props.EnumProperty(
        name="Billboard Mode",
        items=[
            ("OFF", "Off", "No billboard rotation"),
            ("AXIAL", "Axial", "Rotate around branch axis toward camera"),
            ("CAMERA", "Camera-Facing", "Fully face the camera"),
        ],
        default="OFF",
    )
    lod_1_distance: bpy.props.FloatProperty(
        name="LOD 1 Distance",
        description="Distance threshold for LOD 1 switching",
        default=20.0,
        min=0.0,
    )
    cull_distance: bpy.props.FloatProperty(
        name="Cull Distance",
        description="Distance beyond which leaves are removed",
        default=100.0,
        min=0.0,
    )
    enable_normal_transfer: bpy.props.BoolProperty(
        name="Enable Normal Transfer",
        description="Transfer proxy volume normals to leaves for smooth canopy shading",
        default=True,
    )

    def execute(self, context):
        ob = bpy.data.objects.get(self.object_id)
        if ob is not None:
            distribute_leaves(
                ob,
                distribution_mode=self.distribution_mode,
                phyllotaxis_angle=self.phyllotaxis_angle,
                billboard_mode=self.billboard_mode,
                lod_1_distance=self.lod_1_distance,
                cull_distance=self.cull_distance,
                camera=bpy.context.scene.camera,
                enable_normal_transfer=self.enable_normal_transfer,
            )
        return {"FINISHED"}


class QuickGenerateTree(bpy.types.Operator):
    """Generate a procedural tree from species and focused shape settings."""

    bl_idname = "mtree.quick_generate"
    bl_label = "Generate Tree"
    bl_options = {"REGISTER", "UNDO"}

    seed: bpy.props.IntProperty(
        name="Seed", default=0, min=0, description="Random seed (0 = random)"
    )
    preset: bpy.props.EnumProperty(name="Tree Type", items=get_preset_items(), default="OAK")
    add_leaves: bpy.props.BoolProperty(
        name="Add Legacy Leaves",
        default=False,
        description="Add the original high-detail procedural leaves instead of canopy lobes",
    )
    wood_output_profile: bpy.props.EnumProperty(
        name="Wood Output",
        description="Choose original authoring topology or optimized game topology",
        items=WOOD_OUTPUT_PROFILE_ITEMS,
        default=ROBLOX_GAME_BUDGET,
    )
    overall_size: bpy.props.FloatProperty(
        name="Overall Size", default=1.0, min=0.25, max=3.0
    )
    trunk_thickness: bpy.props.FloatProperty(
        name="Trunk Thickness", default=1.0, min=0.25, max=3.0
    )
    branch_length: bpy.props.FloatProperty(
        name="Branch Length", default=1.0, min=0.25, max=2.5
    )
    branch_density: bpy.props.FloatProperty(
        name="Branch Density", default=1.0, min=0.1, max=2.0
    )
    branch_spread: bpy.props.FloatProperty(
        name="Branch Spread", default=1.0, min=0.25, max=1.75
    )
    branch_droop: bpy.props.FloatProperty(
        name="Branch Droop", default=1.0, min=0.0, max=3.0
    )
    randomness: bpy.props.FloatProperty(
        name="Randomness", default=1.0, min=0.0, max=2.0
    )
    secondary_branches: bpy.props.BoolProperty(name="Secondary Branches", default=True)
    use_sidebar_settings: bpy.props.BoolProperty(default=False, options={"HIDDEN"})

    # Maps tree presets to matching leaf presets
    _TREE_TO_LEAF_PRESET = {
        "OAK": "OAK",
        "PINE": "PINE",
    }

    def _load_sidebar_settings(self, context):
        settings = context.scene.mtree_quick_generate_settings
        for field_name in (
            "preset",
            "seed",
            "wood_output_profile",
            "add_leaves",
            "overall_size",
            "trunk_thickness",
            "branch_length",
            "branch_density",
            "branch_spread",
            "branch_droop",
            "randomness",
            "secondary_branches",
        ):
            setattr(self, field_name, getattr(settings, field_name))

    def execute(self, context):
        try:
            if self.use_sidebar_settings:
                self._load_sidebar_settings(context)
            seed = self.seed if self.seed != 0 else randint(0, 10000)
            start_time = time.time()

            cpp_mesh, foliage_anchors, retained_branch_ids = self._generate_tree(seed)
            tree_object = self._create_blender_object(context, cpp_mesh, f"Tree_{seed}")
            preset = TREE_PRESETS.get(self.preset)
            species_label = preset.label if preset is not None else self.preset.title()
            organize_tree_object(
                tree_object,
                generation_seed=seed,
                species_id=self.preset,
                species_label=species_label,
            )
            store_anchor_payload(tree_object, foliage_anchors)
            store_retained_branch_ids(tree_object, retained_branch_ids, foliage_anchors)
            tree_object["mtree_generation_preset"] = self.preset
            tree_object["mtree_wood_output_profile"] = self.wood_output_profile
            tree_object.mtree_foliage_set_id = default_tree_foliage_set_id(
                self.preset, context.scene.mtree_foliage_library_set_id
            )
            tree_object.mtree_foliage_branch_layers = default_foliage_branch_layers(
                self.preset
            )
            for field_name in (
                "overall_size",
                "trunk_thickness",
                "branch_length",
                "branch_density",
                "branch_spread",
                "branch_droop",
                "randomness",
                "secondary_branches",
            ):
                tree_object[f"mtree_{field_name}"] = getattr(self, field_name)

            if self.add_leaves and self.preset != "DEAD_SNAG":
                active_obj = context.view_layer.objects.active
                if active_obj is not None:
                    leaf_obj = self._create_leaf_for_preset(seed)
                    leaf_kwargs = {}
                    preset = TREE_PRESETS.get(self.preset)
                    if preset and preset.leaf_params:
                        leaf_kwargs = preset.leaf_params
                    distribute_leaves(active_obj, leaf_object=leaf_obj, **leaf_kwargs)

            elapsed = time.time() - start_time
            self.report({"INFO"}, f"Generated tree (seed={seed}) in {elapsed:.2f}s")
            return {"FINISHED"}

        except Exception as e:
            self.report({"ERROR"}, f"Failed to generate tree: {str(e)}")
            return {"CANCELLED"}

    def _generate_tree(self, seed: int):
        """Generate tree using C++ library."""
        tree = m_tree.Tree()

        trunk = m_tree.TrunkFunction()
        trunk.seed = seed
        apply_trunk_preset(
            trunk,
            self.preset,
            overall_size=getattr(self, "overall_size", 1.0),
            trunk_thickness=getattr(self, "trunk_thickness", 1.0),
            randomness=getattr(self, "randomness", 1.0),
        )

        branches = m_tree.BranchFunction()
        branches.seed = seed + 1
        apply_preset(
            branches,
            self.preset,
            overall_size=getattr(self, "overall_size", 1.0),
            branch_length=getattr(self, "branch_length", 1.0),
            branch_density=getattr(self, "branch_density", 1.0),
            branch_spread=getattr(self, "branch_spread", 1.0),
            branch_droop=getattr(self, "branch_droop", 1.0),
            randomness=getattr(self, "randomness", 1.0),
        )

        preset = TREE_PRESETS.get(self.preset)
        if (
            preset
            and preset.sub_branches
            and getattr(self, "secondary_branches", True)
        ):
            sub_branches = m_tree.BranchFunction()
            sub_branches.seed = seed + 2
            apply_sub_branch_preset(
                sub_branches,
                self.preset,
                overall_size=getattr(self, "overall_size", 1.0),
                branch_length=getattr(self, "branch_length", 1.0),
                branch_density=getattr(self, "branch_density", 1.0),
                branch_spread=getattr(self, "branch_spread", 1.0),
                branch_droop=getattr(self, "branch_droop", 1.0),
                randomness=getattr(self, "randomness", 1.0),
            )
            branches.add_child(sub_branches)

        trunk.add_child(branches)
        tree.set_trunk_function(trunk)
        tree.execute_functions()

        foliage_anchors = anchors_from_native(m_tree.extract_foliage_anchors(tree))

        mesher = m_tree.ManifoldMesher()
        settings = resolve_wood_mesher_settings(self.wood_output_profile, 32, 4)
        mesher.radial_n_points = settings.radial_resolution
        mesher.smooth_iterations = settings.smooth_iterations
        mesher.longitudinal_stride = settings.longitudinal_stride
        mesher.max_branch_depth = settings.max_branch_depth
        mesher.minimum_branch_radius_ratio = settings.minimum_branch_radius_ratio
        cpp_mesh = mesher.mesh_tree(tree)
        return cpp_mesh, foliage_anchors, list(mesher.retained_branch_ids)

    def _create_blender_object(self, context, cpp_mesh, name: str):
        """Create Blender mesh object from C++ mesh data."""
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)
        context.collection.objects.link(obj)
        context.view_layer.objects.active = obj
        obj.select_set(True)

        create_mesh_from_cpp(mesh, cpp_mesh)
        return obj

    def _create_leaf_for_preset(self, seed: int):
        """Create a unique procedural leaf matching the tree preset."""
        import random

        from .mesh_utils import create_leaf_mesh_from_cpp
        from .resources.node_groups import _get_or_create_resource_collection

        # Pick leaf preset based on tree preset
        if self.preset == "RANDOM":
            leaf_preset_name = random.choice(list(LEAF_PRESETS.keys()))
        else:
            leaf_preset_name = self._TREE_TO_LEAF_PRESET.get(
                self.preset, random.choice(list(LEAF_PRESETS.keys()))
            )

        gen = m_tree.LeafShapeGenerator()
        apply_preset_to_generator(gen, leaf_preset_name)
        gen.seed = seed
        gen.asymmetry_seed = seed

        cpp_mesh = gen.generate()

        obj_name = f"Leaf_{seed}"
        mesh = bpy.data.meshes.new(obj_name)
        obj = bpy.data.objects.new(obj_name, mesh)
        create_leaf_mesh_from_cpp(mesh, cpp_mesh)

        collection = _get_or_create_resource_collection()
        collection.objects.link(obj)
        return obj

    def invoke(self, context, event):
        if self.use_sidebar_settings:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "preset")
        layout.prop(self, "seed")
        layout.prop(self, "wood_output_profile")
        layout.prop(self, "overall_size")
        layout.prop(self, "trunk_thickness")
        layout.prop(self, "branch_length")
        layout.prop(self, "branch_density")
        layout.prop(self, "branch_spread")
        layout.prop(self, "branch_droop")
        layout.prop(self, "randomness")
        layout.prop(self, "secondary_branches")
        layout.prop(self, "add_leaves")


class ResetQuickGenerateOverrides(bpy.types.Operator):
    """Reset focused tree-shape overrides while retaining type and seed."""

    bl_idname = "mtree.reset_quick_generate_overrides"
    bl_label = "Reset Overrides"
    bl_options = {"UNDO"}

    def execute(self, context):
        reset_generation_overrides(context.scene.mtree_quick_generate_settings)
        return {"FINISHED"}


class ExportPivotPainter(bpy.types.Operator):
    """Export Pivot Painter 2.0 data for game engines."""

    bl_idname = "mtree.export_pivot_painter"
    bl_label = "Export Pivot Painter"
    bl_options = {"REGISTER", "UNDO"}

    object_name: bpy.props.StringProperty(name="Object")
    export_format: bpy.props.EnumProperty(
        name="Format",
        items=[
            ("UE5", "Unreal Engine 5", "Export for UE5 with Nanite support"),
            ("UE4", "Unreal Engine 4", "Export for UE4 Pivot Painter 2.0"),
            ("UNITY", "Unity", "Export vertex colors for Unity"),
        ],
        default="UE5",
    )
    texture_size: bpy.props.IntProperty(name="Texture Size", default=1024, min=64, max=4096)
    export_path: bpy.props.StringProperty(
        name="Export Path",
        subtype="DIR_PATH",
        default="//pivot_painter/",
    )

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)
        if obj is None or obj.type != "MESH":
            self.report({"ERROR"}, "Invalid mesh object")
            return {"CANCELLED"}

        mesh_data = obj.data
        if not isinstance(mesh_data, bpy.types.Mesh):
            self.report({"ERROR"}, "Object data is not a mesh")
            return {"CANCELLED"}

        exporter = PivotPainterExporter(
            mesh=mesh_data,
            export_format=ExportFormat[self.export_format],
            texture_size=self.texture_size,
            export_path=self.export_path,
        )

        result = exporter.export(obj.name)

        if result.success:
            self.report({"INFO"}, result.message)
            return {"FINISHED"}
        else:
            self.report({"ERROR"}, result.message)
            return {"CANCELLED"}

    def invoke(self, context, event):
        if context.active_object and context.active_object.type == "MESH":
            self.object_name = context.active_object.name
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "object_name")
        layout.prop(self, "export_format")
        if self.export_format != "UNITY":
            layout.prop(self, "texture_size")
        layout.prop(self, "export_path")


class CreateCanopyLobes(bpy.types.Operator):
    """Create the editable low-poly canopy lobe template library."""

    bl_idname = "mtree.create_canopy_lobes"
    bl_label = "Create Canopy Lobes"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            templates, created = ensure_canopy_templates()
            self.report(
                {"INFO"},
                f"Canopy library ready; created {created}, preserved {len(templates) - created}",
            )
            return {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, f"Failed to create canopy lobes: {exc}")
            return {"CANCELLED"}


class RefreshCanopyLobes(bpy.types.Operator):
    """Generate or refresh the active tree's deterministic canopy lobes."""

    bl_idname = "mtree.refresh_canopy_lobes"
    bl_label = "Generate / Refresh Lobes"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        try:
            foliage, count = refresh_canopy_for_object(context.active_object)
            self.report({"INFO"}, f"Generated {count} canopy lobes in {foliage.name}")
            return {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, f"Failed to refresh canopy lobes: {exc}")
            return {"CANCELLED"}


class CreateFoliageCardTemplate(bpy.types.Operator):
    """Initialize or repair the selected four-slot species foliage set."""

    bl_idname = "mtree.create_foliage_card_template"
    bl_label = "Initialize / Repair Foliage Set"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            collection, templates, created = ensure_foliage_card_set(context)
            self.report(
                {"INFO"},
                f"{collection.name} ready; created {created}, preserved {len(templates) - created}",
            )
            return {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, f"Failed to create foliage card template: {exc}")
            return {"CANCELLED"}


class RefreshFoliageCards(bpy.types.Operator):
    """Generate or refresh the active tree's branch-aligned card pairs."""

    bl_idname = "mtree.refresh_foliage_cards"
    bl_label = "Generate / Refresh Foliage Cards"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        try:
            foliage, clusters, cards = refresh_foliage_cards_for_object(context.active_object)
            self.report(
                {"INFO"},
                f"Generated {clusters} foliage clusters / {cards} cards in {foliage.name}",
            )
            return {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, f"Failed to refresh foliage cards: {exc}")
            return {"CANCELLED"}


class GenerateLeaf(bpy.types.Operator):
    """Generate a procedural leaf mesh from LeafShapeNode parameters."""

    bl_idname = "mtree.generate_leaf"
    bl_label = "Generate Leaf"
    bl_options = {"REGISTER", "UNDO"}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        node_tree = bpy.data.node_groups.get(self.node_tree_name)
        if not node_tree:
            self.report({"ERROR"}, "Node tree not found")
            return {"CANCELLED"}
        node = node_tree.nodes.get(self.node_name)
        if node and hasattr(node, "generate_leaf"):
            node.generate_leaf()
            return {"FINISHED"}
        self.report({"ERROR"}, "Leaf shape node not found")
        return {"CANCELLED"}


class ApplyLeafPreset(bpy.types.Operator):
    """Apply a species preset to a LeafShapeNode."""

    bl_idname = "mtree.apply_leaf_preset"
    bl_label = "Apply Leaf Preset"
    bl_options = {"REGISTER", "UNDO"}

    preset: bpy.props.EnumProperty(
        name="Preset",
        items=get_leaf_preset_items(),
    )
    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        node_tree = bpy.data.node_groups.get(self.node_tree_name)
        if not node_tree:
            return {"CANCELLED"}
        node = node_tree.nodes.get(self.node_name)
        if node and hasattr(node, "apply_preset"):
            node.apply_preset(self.preset)
        return {"FINISHED"}


class ApplyBranchNodePreset(bpy.types.Operator):
    """Apply a preset to a branch node."""

    bl_idname = "mtree.apply_branch_node_preset"
    bl_label = "Apply Preset"
    bl_options = {"REGISTER", "UNDO"}

    preset: bpy.props.EnumProperty(name="Preset", items=get_preset_items())
    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        node_tree = bpy.data.node_groups.get(self.node_tree_name)
        if not node_tree:
            return {"CANCELLED"}
        node = node_tree.nodes.get(self.node_name)
        if node and hasattr(node, "apply_preset"):
            node.apply_preset(self.preset)
        return {"FINISHED"}


class ApplyTrunkNodePreset(bpy.types.Operator):
    """Apply a preset to a trunk node."""

    bl_idname = "mtree.apply_trunk_node_preset"
    bl_label = "Apply Preset"
    bl_options = {"REGISTER", "UNDO"}

    preset: bpy.props.EnumProperty(name="Preset", items=get_preset_items())
    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        node_tree = bpy.data.node_groups.get(self.node_tree_name)
        if not node_tree:
            return {"CANCELLED"}
        node = node_tree.nodes.get(self.node_name)
        if node and hasattr(node, "apply_preset"):
            node.apply_preset(self.preset)
        return {"FINISHED"}


class ApplyGrowthNodePreset(bpy.types.Operator):
    """Apply a preset to a growth node."""

    bl_idname = "mtree.apply_growth_node_preset"
    bl_label = "Apply Growth Preset"
    bl_options = {"REGISTER", "UNDO"}

    preset: bpy.props.EnumProperty(name="Preset", items=get_growth_preset_items())
    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        node_tree = bpy.data.node_groups.get(self.node_tree_name)
        if not node_tree:
            return {"CANCELLED"}
        node = node_tree.nodes.get(self.node_name)
        if node and hasattr(node, "apply_preset"):
            node.apply_preset(self.preset)
        return {"FINISHED"}


# Registration

_classes = [
    ExecuteNodeFunction,
    AddLeavesModifier,
    QuickGenerateTree,
    ResetQuickGenerateOverrides,
    CreateCanopyLobes,
    RefreshCanopyLobes,
    CreateFoliageCardTemplate,
    RefreshFoliageCards,
    ExportPivotPainter,
    GenerateLeaf,
    ApplyLeafPreset,
    ApplyBranchNodePreset,
    ApplyTrunkNodePreset,
    ApplyGrowthNodePreset,
]


def register():
    for cls in _classes:
        register_class(cls)


def unregister():
    for cls in _classes:
        unregister_class(cls)
