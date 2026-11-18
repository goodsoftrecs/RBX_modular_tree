# Canopy Lobes Design

## Purpose

Replace the upstream per-leaf foliage path for Roblox-targeted trees with a small number of
low-poly canopy volumes. The new path must support fast visual iteration, deterministic refresh,
and an eventual alpha-cutout foliage texture without requiring the artist to model canopy shapes
from scratch.

## Approved Visual Direction

Use multiple perforated canopy lobes rather than individual leaves or one shell around the whole
tree. The first version uses solid green preview materials; the visible holes will later come from
an RGBA foliage texture rather than expensive mesh topology.

The reusable lobe library contains three editable templates:

- `Canopy_Round`: central crown volume.
- `Canopy_Wide`: lateral branch volume.
- `Canopy_Tip`: upper and outer crown volume.

Each template is a closed, irregular, UV-mapped mesh with roughly 30-60 triangles. Generated
trees combine placed lobes into one foliage mesh so Roblox import does not create one MeshPart per
lobe.

## Scene Structure

```text
Scene Collection
├── MTree_CanopyLibrary
│   ├── Canopy_Round
│   ├── Canopy_Wide
│   └── Canopy_Tip
│
└── MTree_GeneratedTrees
    └── Tree_0538
        ├── Tree_0538_Root
        ├── Tree_0538_Wood
        └── Tree_0538_Foliage
```

The template library is editable authoring state and is never treated as generated tree output.
Each generated tree has a stable identifier shared by its root, wood, and foliage objects.

## Controls

The MTree sidebar gains a `Canopy Lobes` section with:

- `Lobe Count`: integer, default `8`, range `1-32`, saved per tree.
- `Lobe Scale`: float multiplier, default `1.0`, saved per tree.
- `Canopy Seed`: integer, defaulting to the tree generation seed, saved per tree.
- `Create Canopy Lobes`: creates any missing editable templates without overwriting existing
  artist edits.
- `Generate / Refresh Lobes`: resolves the active tree and replaces only its foliage output.

The active object may be either the tree's wood or foliage object. Both resolve to the same tree.
If no foliage exists, Refresh performs the first generation.

## Deterministic Placement

Placement reads the generated wood mesh attributes instead of relying on the discarded native
tree graph. It derives retained branch endpoints from `stem_id`, `pivot_position`, `direction`,
`hierarchy_depth`, and vertex positions, then selects spatially distributed anchors.

The requested lobe count is exact when the mesh supplies enough anchors. Template selection is
automatic:

- central anchors use `Canopy_Round`;
- lateral anchors use `Canopy_Wide`;
- high and outer anchors use `Canopy_Tip`.

Base lobe size derives from crown dimensions and lobe count. `Lobe Scale` multiplies that base.
The canopy seed controls deterministic anchor tie-breaking, template variation, rotation, and
scale variation. Refreshing unchanged inputs reproduces unchanged output.

## Legacy Trees

New quick-generated trees store their generation seed and ownership metadata explicitly. A legacy
wood object named `Tree_<number>` may be adopted on first canopy refresh: its seed is parsed from
the name, metadata is stored, and it is organized into the generated-tree structure. If no seed can
be recovered, canopy seed `0` is used and remains editable.

## Non-Goals

- Do not optimize or remove the existing procedural-leaf implementation in this slice.
- Do not create the final foliage texture.
- Do not add wind or per-lobe animation.
- Do not export or configure Roblox `SurfaceAppearance` yet.
- Do not overwrite artist-edited lobe templates during ordinary initialization.

## Acceptance Criteria

- Three editable lobe templates can be created from the sidebar.
- A selected generated or legacy tree can produce one foliage mesh with the requested lobe count.
- Refresh replaces only foliage and preserves wood, templates, settings, and arrangement seed.
- Resizing a template and refreshing changes the selected tree's foliage geometry.
- Selecting either wood or foliage resolves the same owning tree.
- The same inputs reproduce identical foliage vertices and faces.

