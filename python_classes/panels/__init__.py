from __future__ import annotations

import bpy
from bpy.utils import register_class, unregister_class

from ..canopy_lobes import find_wood_for_object
from ..presets import TREE_PRESETS


class MTREE_PT_QuickGenerate(bpy.types.Panel):
    """Quick tree generation panel in the 3D View sidebar"""

    bl_label = "MTree"
    bl_idname = "MTREE_PT_quick_generate"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MTree"

    def draw(self, context):
        layout = self.layout

        # Quick generate section
        box = layout.box()
        box.label(text="Tree Generation", icon="OUTLINER_OB_MESH")
        settings = context.scene.mtree_quick_generate_settings
        box.prop(settings, "preset")
        box.prop(settings, "seed")
        box.prop(settings, "wood_output_profile")

        shape_box = box.box()
        shape_box.label(text="Shape Overrides")
        shape_box.prop(settings, "overall_size")
        shape_box.prop(settings, "trunk_thickness")
        shape_box.prop(settings, "branch_length")
        shape_box.prop(settings, "branch_density")
        shape_box.prop(settings, "branch_spread")
        shape_box.prop(settings, "branch_droop")
        shape_box.prop(settings, "randomness")

        preset = TREE_PRESETS.get(settings.preset)
        secondary_row = shape_box.row()
        secondary_row.enabled = bool(preset and preset.sub_branches)
        secondary_row.prop(settings, "secondary_branches")
        shape_box.operator(
            "mtree.reset_quick_generate_overrides", text="Reset Overrides"
        )

        leaf_row = box.row()
        leaf_row.enabled = settings.preset != "DEAD_SNAG"
        leaf_row.prop(settings, "add_leaves")
        generate = box.operator("mtree.quick_generate", text="Generate Tree")
        generate.use_sidebar_settings = True

        if settings.branch_density > 1.25:
            box.label(text="Higher density may exceed the ~3K target", icon="INFO")

        canopy_box = layout.box()
        canopy_box.label(text="Foliage Cards", icon="OUTLINER_OB_MESH")
        canopy_box.prop(context.scene, "mtree_foliage_library_set_id")
        canopy_box.operator(
            "mtree.create_foliage_card_template", text="Initialize / Repair Foliage Set"
        )

        wood = find_wood_for_object(context.active_object)
        if wood is not None:
            canopy_box.prop(wood, "mtree_foliage_set_id")
            canopy_box.prop(wood, "mtree_foliage_cluster_count")
            canopy_box.prop(wood, "mtree_foliage_top_tip_pairs")
            canopy_box.prop(wood, "mtree_foliage_card_scale")
            canopy_box.prop(wood, "mtree_foliage_branch_layers")
            primary_length_row = canopy_box.row()
            primary_length_row.enabled = (
                wood.mtree_foliage_branch_layers == "PRIMARY_SECONDARY"
            )
            primary_length_row.prop(wood, "mtree_foliage_primary_card_length")
            canopy_box.prop(wood, "mtree_foliage_branch_card_length")
            canopy_box.prop(wood, "mtree_foliage_length_variation")
            canopy_box.prop(wood, "mtree_foliage_branch_spacing")
            canopy_box.prop(wood, "mtree_foliage_branch_distance")
            canopy_box.prop(wood, "mtree_foliage_texture_rotation")
            canopy_box.prop(wood, "mtree_foliage_pair_rotation")
            canopy_box.prop(wood, "mtree_foliage_canopy_rotation")
            canopy_box.prop(wood, "mtree_foliage_seed")
        refresh_row = canopy_box.row()
        refresh_row.enabled = wood is not None
        refresh_row.operator(
            "mtree.refresh_foliage_cards", text="Generate / Refresh Foliage Cards"
        )

        # Tips section
        layout.separator()
        box = layout.box()
        box.label(text="Advanced Options", icon="NODETREE")
        row = box.row()
        row.label(text="Use the MTree Node Editor")
        row = box.row()
        row.label(text="for full control over")
        row = box.row()
        row.label(text="tree parameters.")


def register():
    register_class(MTREE_PT_QuickGenerate)


def unregister():
    unregister_class(MTREE_PT_QuickGenerate)
