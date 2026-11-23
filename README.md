# RBX Modular Tree

[![Build and Release](https://github.com/GoodPie/modular_tree/actions/workflows/CD.yml/badge.svg)](https://github.com/GoodPie/modular_tree/actions/workflows/CD.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A Blender tree-authoring fork focused on producing practical game-ready geometry for the RBX
world-authoring pipeline.

This fork is based on [GoodPie's Modular Tree](https://github.com/GoodPie/modular_tree). The
upstream authoring output remains available; Quick Generate defaults to the RBX game-budget profile.

> **Note:** This is a maintained fork of [Mtree by MaximeHerpin](https://github.com/MaximeHerpin/modular_tree). Some features are no longer best practice and work is being done to implement these properly

## Features

- **Quick Generate** - Sidebar generation for Oak, Birch, Pine, Cedar, Walnut, Sequoia,
  Hemlock, Teak, Dead/Snag, and Random trees
- **Node-based workflow** - Build trees visually by connecting nodes for full control
- **Procedural generation** - Control trunk, branches, and leaves with parameters
- **Multi-level branching** - Chain branch nodes for complex tree structures
- **Crown shapes** - 8 botanical envelope shapes (conical, spherical, flame, etc.) based on Weber & Penn
- **L-system growth** - Biologically-inspired growth simulation with apical dominance
- **Realistic physics** - Gravity, stiffness, and natural spiral patterns (phyllotaxis)
- **Leaf distribution** - Automatic leaf placement on thin branches via geometry nodes
- **Pivot Painter 2.0 export** - Export wind animation data for Unreal Engine 5
- **Non-destructive** - Adjust parameters and regenerate anytime
- **Roblox Game wood profile** - Lowers radial and lengthwise trunk/branch topology while
  preserving forks, branch attachment points, and tips
- **Aggressive ~3K-triangle wood profile** - Removes deeper and very thin twig families before
  their junctions are meshed; representative Oak seeds generate near the target triangle count
- **Virtual-branch foliage cards** - Extracts placement anchors from the complete procedural tree
  before wood pruning, then combines deterministic shallow-V card pairs into one foliage mesh

## Requirements

- Blender 4.3 or later

## Installation

### Blender Extensions

Find the extension on the Blender extension platform

https://extensions.blender.org/add-ons/modular-tree/

### Local Installation

1. Build or download the RBX fork zip (`rbx_modular_tree_*.zip`)
2. In Blender: Edit -> Preferences -> Add-ons -> Install
3. Select the downloaded `.zip` file
4. Enable "RBX Modular Tree" in the addon list

## Quick Start

### Quick Generate (Easiest)
1. Open the **3D View** sidebar (press `N`)
2. Select the **MTree** tab
3. Choose a **Tree Type**, seed, and focused shape overrides
4. Leave **Wood Output** on the default **Roblox Game (~3K Tris)** profile
5. Click **Generate Tree**

Generated hierarchies use readable per-species numbering such as `Oak_1`, `Oak_2`, and `Birch_1`.
The collection, root, wood, and generated foliage share that base name while internal UUID metadata
continues to provide stable ownership.

Each generated tree collection is also linked, not copied, beneath
`RBX_PrefabLibrary_Placements`. Editing the tree through either Outliner location edits the same
collection. MTree creates the required ground-origin `RBX_GroundAnchor_Att` marker and initializes
the RBX prefab fields with category `tree`, upright alignment, and `rbx_enabled = false`. Select
the tree collection in either location and use RBX World Authoring's
**Initialize/Update Selection as Prefab** when it is ready for placement and FBX refresh.

Focused overrides adjust Overall Size, Trunk Thickness, Branch Length, Branch Density, Branch
Spread, Branch Droop, Randomness, and the species' Secondary Branch layer. Neutral `1.0` values
preserve the authored species silhouette. Trunk Thickness changes radii without adding radial
rings; density and secondary branches are the controls most likely to increase topology.

### Foliage Cards

1. In **Foliage Cards**, choose Oak, Birch, Pine, Cedar, Walnut, Sequoia, Hemlock, or Teak.
2. Click **Initialize / Repair Foliage Set**. This creates one species collection containing a text
   label and four editable cards: Large A, Large B, Small A, and Small B.
3. Edit the one shared material and assign your transparent `2 x 2` branch atlas. The upper cards
   use the two upper quadrants; the lower cards use the two lower quadrants.
4. Shape, rotate, and scale the four source cards independently. Re-running the initializer
   preserves valid cards and creates only a missing slot.
5. Generate a tree with **Add Legacy Leaves** disabled (the default), then select its wood object.
   A matching initialized species set is selected automatically; **Tree Foliage Set** can override
   it.
6. Adjust exact **Foliage Cluster Count** (up to `512`), **Top Tip Pairs** (`0` to `2`),
   **Card Scale** (up to `12x`), **Branch Start Layers**, **Primary Card Length** (`0.5x` to `4.0x`), **Branch Card Length**
   (`0.5x` to `3.0x`), **Length Variation** (`0%` to `50%`), **Branch Spacing** (`0.1x` to
   `3.0x`), signed **Branch Distance**, rotations, or **Foliage Seed**.
7. Click **Generate / Refresh Foliage Cards**.

The atlas layout is fixed: Large A is top-left, Large B is top-right, Small A is bottom-left, and
Small B is bottom-right. Keep branch pixels and transparent padding inside each quadrant. All four
source cards in a species set must share exactly one material datablock.

The exact top-right UV corner of every quadrant is the branch attachment point. Put the end of each
photographed branch there; generated cards pin that corner to their physical or virtual branch and
extend from that corner toward the card's geometric center. **Branch Distance** offsets the two
planes independently along their perpendicular normals: `0` sits on the branch, positive values
move both planes outward, and negative values bury them into the branch. Card Scale grows or shrinks
around the pinned corner, so changing scale does not move the attachment.

Each cluster contains two static cards in a fixed shallow V aligned to a branch from the complete
procedural graph. The optimized wood mesh may omit that branch; its lightweight anchor still drives
foliage placement. Thirty clusters therefore create 60 quad cards, approximately 120 triangles,
one foliage object, and one material. Each pair deterministically chooses one of the four variants,
and both planes in that pair use the same variant. The per-species collection exists only to keep
the four editable sources organized; it does not split the generated tree into four objects.

The native mesher records the exact stable branch IDs retained in the optimized wood; placement no
longer guesses physical branches from mesh proximity. Foliage-bearing secondary branches begin at
their explicit progress-zero connection anchors and extend toward their tips. Retained physical
branches are selected before branches omitted from the optimized wood. **Branch Start Layers** can
use secondary connections only or include the primary connections where major limbs meet the
trunk. Pine, Cedar, Sequoia, and Hemlock default to **Primary + Secondary**; broadleaf presets
default to **Secondary Only**. Every selected branch receives its connection anchor first, and
additional requested clusters advance outward.

**Top Tip Pairs** reserves zero, one, or two clusters at the highest terminal trunk anchor before
that branch order is filled. Pine, Cedar, Sequoia, and Hemlock default to one tip pair; broadleaf
presets default to zero. A second tip pair shares the exact pinned attachment and is rolled 90
degrees around the terminal leader. These pairs count inside **Foliage Cluster Count**, so a count
of 30 with one tip pair produces one apex cluster plus 29 branch clusters, not 31 total clusters.
Tip cards reuse **Branch Card Length** and **Length Variation**.

**Primary Card Length** controls trunk-origin cards independently and defaults to `2.0x`.
**Branch Card Length** controls secondary cards and defaults to `1.5x`. Both scale only the authored
attachment-to-center axis around the pinned corner and do not widen the card. **Length Variation** applies deterministic
per-cluster variation around that value, with both planes in a pair always sharing one length; zero
is fully uniform. Variation changes geometry only and never reshuffles placement or atlas variants.

**Branch Spacing** independently multiplies the minimum separation derived from the edited card
footprint and **Card Scale**. Lower values pack outward placements more tightly and higher values
skip farther along each branch. **Foliage Cluster Count** remains exact and cumulative: raising it
preserves existing placements and appends new ones. Automatic card size uses the fixed 30-cluster
reference density, so raising count does not shrink existing cards.

Refresh replaces only the selected tree's combined foliage mesh. It preserves the wood, settings,
seed, and editable templates, and selection may start from either wood or foliage. Trees generated
before complete-graph anchor persistence, progress-zero junction anchors, or retained-branch ID
reporting were added must be regenerated; the add-on fails explicitly instead of falling back to
stale or guessed branch data. Refreshing foliage alone cannot add the required tree metadata.

The length, variation, spacing, and three rotation controls are per tree. Texture Rotation transforms UVs inside each selected
quadrant and cannot sample a neighboring atlas slot; Card Pair Rotation rolls each shallow-V pair
around its virtual branch; Canopy Rotation turns all foliage around the tree-local vertical axis.
Wind and automatic LOD generation remain later stages and do not require changing anchor extraction.

### Node Editor (Full Control)
1. Open a **Node Editor** and select **Mtree** from the tree type dropdown
2. Add a **Tree Mesher** node (Shift+A)
3. Add a **Trunk** node and connect Tree Mesher's output to Trunk's input
4. Add a **Branches** node and connect Trunk's output to Branches' input
5. Click **Generate Tree** in the Tree Mesher node
6. (Optional) Click **Add Leaves** to distribute leaves on the tree

The node editor retains the original **Authoring** wood profile as its default. Quick Generate
defaults to **Roblox Game (~3K Tris)**. The intermediate Roblox Game profile uses 8-sided rings,
one smoothing pass, and junction-safe lengthwise ring thinning. Leaf optimization is separate.

For a more aggressive result, select **Roblox Game (~3K Tris)**. It preserves the trunk and
two branch generations, uses six-sided wood rings without a smoothing subdivision, thins rings
lengthwise, and omits deeper or extremely thin twig families before mesh construction. The ~3K
label is a global target rather than a hard cap. Stock validation currently ranges from very sparse
Dead/Snag geometry through a roughly 4.3K Pine; seeds and topology-sensitive overrides can vary,
so inspect Blender's triangle count before export.

**Tip:** Select a Branch node and press `N` to see organized parameter sections with descriptions,
plus the same species preset buttons used by Quick Generate.

## Node Types

| Node | Description |
|------|-------------|
| **Tree Mesher** | Generates the final mesh; connect to Trunk |
| **Trunk** | Creates the main trunk with length, radius, and shape controls |
| **Branches** | Adds branches with density, angle, gravity, and split options |
| **Growth** | L-system style growth with apical dominance and iterations |
| **Radius Override** | Fine-tunes branch thickness along their length |
| **Random Value** | Generates random values for parameter variation |
| **Ramp** | Creates gradient values from start to end of branches |

## Customization

### Branch Parameters
Use the **Presets** section in the inspector panel (`N` key) to apply a Quick Generate species
configuration or manually adjust:
- **Seed** - Controls randomization (same seed = same tree)
- **Length/Radius** - Size and thickness
- **Up Attraction/Gravity** - How branches grow relative to gravity
- **Split** - Probability and angle of branch splitting
- **Phyllotaxis** - Spiral angle between branches (137.5 is the golden angle)
- **Crown Shape** - Control tree silhouette (Cylindrical, Conical, Spherical, Flame, etc.)

### Crown Shape
Crown Shape controls branch lengths based on height, creating realistic tree silhouettes. Available in the Branch node inspector panel under "Crown Shape":

| Shape | Use Case |
|-------|----------|
| Cylindrical | Default, uniform branches |
| Conical | Pine, fir, spruce (Christmas tree) |
| Spherical | Oak, maple (round crown) |
| Hemispherical | Dome-shaped canopy |
| Flame | Cedar, cypress (pointed top) |
| Inverse Conical | Wide bottom, narrow top |

Enable **Preview in Viewport** to visualize the envelope. See [Crown Shape Guide](docs/crown_shape_guide.md) for details.

### Growth Parameters (L-system)
- **Iterations** - Number of growth cycles
- **Apical Dominance** - How much the main stem suppresses side branches
- **Grow/Split/Cut Thresholds** - Control branching behavior
- **Gravitropism** - Response to gravity direction

### Leaf Generation

Mtree generates fully procedural 3D leaves from math — no hand-modeling or textures needed. Each leaf is built through a pipeline:

1. **Shape** — The outline is created using the [Superformula](https://en.wikipedia.org/wiki/Superformula), a single equation that can produce round, pointed, heart-shaped, or star-like forms by adjusting a few parameters.
2. **Edge detail** — Teeth, scallops, or lobes are added to the outline to match real leaf margin types (serrate, dentate, crenate, lobed).
3. **Vein network** — Veins grow using [space colonization](https://algorithmicbotany.org/papers/venation.sig2005.pdf), which scatters "growth hormone" points across the leaf and lets veins grow toward them — producing realistic branching patterns that fill the available space.
4. **Surface curvature** — The flat mesh is bent with midrib curvature, cross-cupping, edge curl, and raised ridges along vein paths.

Species presets (Oak, Maple, Birch, Willow, Pine) combine these parameters to match real leaves. See the [Leaf Generation Guide](docs/leaf_generation.md) for a full walkthrough.

### Leaf Distribution
After generating a tree, click "Add Leaves" in Tree Mesher to configure:
- **Density** - Leaves per area
- **Max Radius** - Only place leaves on thin branches
- **Scale/Rotation Variation** - Natural randomness
- **Leaf Object** - Use a custom leaf mesh

### Pivot Painter 2.0 Export (UE5)



Export hierarchical wind animation data for Unreal Engine 5:

1. Generate a tree using the **Tree Mesher** node
2. In the Node Editor, add an **Export > Pivot Painter** node
3. Connect your Tree Mesher output to the Pivot Painter node
4. Set the export path and click **Export**

This creates two EXR textures and a UV2 layer compatible with Epic's
`PivotPainter2FoliageShader` material function.

See [UE5 Material Setup Guide](python_classes/pivot_painter/UE5_MATERIAL_SETUP.md)
for detailed import and material configuration instructions.

> **Note:** Currently only Unreal Engine 5 export is fully tested. I am working towards testing properly in Unity

## Development

This project uses modern Python tooling:

- **[uv](https://docs.astral.sh/uv/)** - Fast Python package manager (used in CI)
- **[Ruff](https://docs.astral.sh/ruff/)** - Fast Python linter and formatter
- **[pre-commit](https://pre-commit.com/)** - Git hooks for code quality
- **[clang-format](https://clang.llvm.org/docs/ClangFormat.html)** - C++ code formatting

To set up the development environment:

```bash
# Install pre-commit hooks (requires uv)
uvx pre-commit install
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full development setup and build instructions.

## Contributing

For detailed build instructions, architecture overview, and C++ library usage, see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

- Blender addon: [GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html)
- Core library: [MIT](https://choosealicense.com/licenses/mit/)

## Credits

**Maintainer:** [GoodPie](https://github.com/GoodPie)
**Original Author:** [MaximeHerpin](https://github.com/MaximeHerpin)
