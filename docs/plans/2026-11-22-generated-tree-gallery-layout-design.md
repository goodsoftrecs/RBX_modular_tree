# Generated Tree Gallery Layout Design

## Goal

Keep MTree-generated prefab sources visually inspectable in Blender without overlapping RBX
foliage authoring content or other trees.

## Layout Contract

- `MTree_GeneratedTrees` remains the organizational root and every generated tree remains linked
  into `RBX_PrefabLibrary_Placements`.
- Each species owns one row. Numbered variations of that species are ordered left-to-right by
  `mtree_tree_number`.
- Rows begin beyond the positive-Y RBX foliage authoring band.
- Every tree root is placed at world `Z = 350` to clear generated terrain preview meshes.
- Packing uses the complete generated tree's world-space mesh bounds, including wood and generated
  foliage. A generous fixed gallery aisle is added between neighboring bounds on both axes.
- Layout moves only each tree's root Empty. Wood, foliage, and `RBX_GroundAnchor_Att` remain children
  and therefore move as one prefab without changing their tree-local relationship.
- Generating a tree, repairing an organized tree, or refreshing its foliage reflows the complete
  gallery. A manual re-layout operator repairs existing scenes without regeneration.

## Failure Behavior

Collections with duplicate tree identity or missing required roots fail explicitly. Legacy
organized trees without species metadata use a final legacy row rather than overlapping a species
row.

## Validation

- Variations of one species share a row and have clear non-overlapping X bounds.
- Different species occupy distinct rows with clear non-overlapping Y bounds.
- Root, wood, foliage, and ground anchor preserve their local transforms while the root moves.
- Re-layout is deterministic and idempotent.
- RBX prefab linkage and disabled-by-default authoring metadata remain unchanged.
