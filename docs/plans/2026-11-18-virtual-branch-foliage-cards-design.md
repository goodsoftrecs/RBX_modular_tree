# Virtual Branch Foliage Cards Design

## Purpose

Replace the solid canopy-lobe presentation with low-cost alpha-cutout foliage cards while keeping
the optimized Roblox wood mesh. Foliage placement must retain the silhouette and coverage of the
complete procedural tree, including branches omitted from the final wood geometry.

## Core Decision

MTree keeps its complete procedural branch graph until `ManifoldMesher` constructs the final mesh.
The add-on will extract a lightweight foliage-anchor cloud from that full graph before meshing and
then generate the existing reduced wood output independently. The complete high-detail wood mesh is
never created or stored.

Each selected foliage anchor receives two copies of one editable card template. The copies form a
fixed shallow V around the virtual branch direction. They are static 3D cards, not camera-facing
billboards.

## Data Flow

```text
Tree seed and preset
        |
        v
Complete MTree branch graph
        |------------------------------|
        v                              v
Dense foliage anchors           Optimized wood mesher
        |                              |
        v                              v
Blender-only tree metadata       3-5K triangle wood mesh
        |
        v
Deterministic anchor selection
        |
        v
Shallow-V card pairs
        |
        v
One combined foliage mesh and one material
```

## Anchor Contract

Each anchor records only the information needed to place a foliage cluster:

- position in tree-local space;
- branch tangent/direction;
- branch radius;
- hierarchy depth;
- stable branch identity;
- normalized progress along its branch when available.

Anchors are sampled from the full graph, including nodes later excluded by branch-depth or radius
pruning. Trunk and thick interior locations are excluded from foliage placement. Selection favors
smaller, deeper, outer branch locations while remaining deterministic for a given tree and foliage
seed.

The anchor payload is stored on the generated wood object as Blender-only metadata so foliage can be
refreshed after reopening the `.blend` without regenerating the tree. It does not create an exportable
scene object or add geometry to the Roblox prefab.

## Card Template And Output

The reusable library contains one editable mesh object:

- `FoliageCard_Template`

The first version uses one full-range `0-1` UV layout and one material. The user supplies a single
RGBA twig-and-leaf texture. A later atlas upgrade can select different UV rectangles without changing
anchor extraction or card placement.

At every selected anchor, the generator creates a shallow-V pair:

- both cards share the same origin and UVs;
- their long axes follow the virtual branch;
- their normals rotate to opposite sides of the branch by half the fixed V angle;
- deterministic scale, roll, and position variation reduce repetition.

All card pairs are combined into one foliage mesh owned by the tree. A cluster count of 30 therefore
creates 60 quad cards and approximately 120 triangles.

## Scene Organization

```text
MTree_FoliageLibrary
└── FoliageCard_Template

MTree_GeneratedTrees
└── Tree_####
    ├── Tree_####_Root
    ├── Tree_####_Wood
    └── Tree_####_Foliage
```

The anchor payload lives on `Tree_####_Wood`; no hidden anchor object is added to the collection.

## Authoring Controls

The MTree sidebar exposes a primary `Foliage Cards` workflow:

- `Create Foliage Card Template`: creates a missing template without overwriting artist edits;
- `Foliage Cluster Count`: exact number of shallow-V pairs;
- `Card Scale`: multiplier over automatically derived size;
- `Foliage Seed`: defaults to the tree generation seed;
- `Generate / Refresh Foliage Cards`: safely replaces foliage for the selected tree.

The initial V angle is fixed near 55 degrees. It becomes a user control only if visual testing shows
that a fixed value is insufficient.

The existing canopy-lobe implementation remains available internally during the prototype but is no
longer the primary visible workflow.

## Failure Handling

- Missing dense anchors fail explicitly instead of silently pretending reduced endpoints are the full
  canopy. Trees created before this feature must be regenerated to receive the dense anchor payload.
- Missing or invalid card templates fail without deleting existing foliage.
- New foliage is built and validated before old foliage is removed.
- Empty eligible-anchor sets fail with a clear message identifying the selected tree.
- Template material and UV data are preserved when the output mesh is assembled.

## Performance Contract

- Default target: 25-40 clusters per tree.
- One cluster: two quad cards, four triangles total.
- One tree: one combined foliage mesh and one material.
- Cards use hard alpha cutouts; soft partial transparency is not part of this design.
- Roblox collision, touch, and query behavior remain disabled for foliage during import/setup.
- The later Roblox test target is a worst-case view containing 50-70 trees; transparency overdraw,
  not card triangle count, is the principal rendering risk.

## Validation

- Identical graph, cluster count, scale, and seed produce identical anchors and card transforms.
- Anchors include branches omitted by the configured optimized mesher.
- Trunk and thick interior nodes are not selected as foliage clusters.
- Requested cluster count produces exactly twice as many cards.
- Each pair forms the fixed shallow V and follows its branch tangent.
- Refresh replaces only the tree's foliage and preserves wood and ownership metadata.
- Editing the template changes the next refresh.
- Thirty clusters produce one foliage mesh, one material, 60 cards, and approximately 120 triangles.

## Non-Goals

- Camera-facing runtime billboards.
- Wind animation or per-card runtime movement.
- Multiple atlas regions in the first implementation.
- Roblox-side foliage generation.
- Generating or retaining the complete high-detail wood mesh.
- Automatic LOD generation in the first implementation.

