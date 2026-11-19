from . import (
    canopy_lobes,
    foliage_cards,
    nodes,
    operators,
    panels,
    quick_generate_settings,
    viewport,
)


def register():
    canopy_lobes.register_properties()
    foliage_cards.register_properties()
    quick_generate_settings.register()
    operators.register()
    nodes.register()
    panels.register()
    viewport.register()


def unregister():
    viewport.unregister()
    operators.unregister()
    nodes.unregister()
    panels.unregister()
    quick_generate_settings.unregister()
    foliage_cards.unregister_properties()
    canopy_lobes.unregister_properties()
