# Trunk-Tip Foliage Pairs Design

## Purpose

Close the empty terminal-leader silhouette on conifers with a small, explicit number of foliage-card
pairs attached to the very top of the main trunk.

## Control and Defaults

- Add `Top Tip Pairs`, an integer per-tree control from `0` to `2`.
- Pine, Cedar, Sequoia, and Hemlock default to `1`.
- Broadleaf species default to `0`.
- `0` disables the feature completely.
- Existing trees that have never set the property receive their species default on first refresh;
  an artist-set value is never overwritten.

## Placement and Count

- Select one terminal anchor from the depth-zero trunk: the terminal candidate with the greatest
  world-space height, with deterministic tie-breaking.
- Tip pairs are emitted before primary connections, secondary connections, and outward anchors.
- Tip pairs count inside the exact `Foliage Cluster Count`; they are not additional geometry.
- If the requested cluster count is smaller than `Top Tip Pairs`, emit only as many tip pairs as fit.
- One pair uses the normal shallow-V orientation aligned to the terminal trunk direction.
- A second pair shares the same pinned attachment anchor and is rolled 90 degrees around the trunk
  direction to complete the apex silhouette.

## Geometry

- Tip cards use the existing `Branch Card Length` and `Length Variation` controls.
- Length scaling remains longitudinal-only around the atlas top-right attachment corner.
- Both planes in each pair use the same atlas tile and varied length, preserving the established
  foliage-card contract.

## Validation

- Pure tests prove tip priority, terminal-anchor selection, exact counts, disabling, count clamping,
  deterministic variation, and the 90-degree second-pair roll.
- Blender integration proves species defaults, metadata, property bounds, and exact output geometry.

