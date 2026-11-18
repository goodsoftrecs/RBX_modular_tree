from __future__ import annotations

import bpy
from bpy.utils import register_class, unregister_class

from ..canopy_lobes import find_wood_for_object


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
        box.label(text="Quick Generate", icon="OUTLINER_OB_MESH")
        box.operator("mtree.quick_generate", text="Generate Tree")

        canopy_box = layout.box()
        canopy_box.label(text="Canopy Lobes", icon="OUTLINER_OB_META")
        canopy_box.operator("mtree.create_canopy_lobes", text="Create Canopy Lobes")

        wood = find_wood_for_object(context.active_object)
        if wood is not None:
            canopy_box.prop(wood, "mtree_lobe_count")
            canopy_box.prop(wood, "mtree_lobe_scale")
            canopy_box.prop(wood, "mtree_canopy_seed")
        refresh_row = canopy_box.row()
        refresh_row.enabled = wood is not None
        refresh_row.operator("mtree.refresh_canopy_lobes", text="Generate / Refresh Lobes")

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
