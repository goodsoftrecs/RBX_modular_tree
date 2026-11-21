# Secondary-Branch Long Foliage Card Design

## Purpose

Reduce the number of foliage clusters needed for a convincing canopy by attaching longer card
pairs at foliage-bearing secondary-branch connections. Preserve explicit artist control: cluster
count remains exact, card length is literal, and no automatic coverage system silently reduces or
changes the requested output.

## Approved Controls

- `Foliage Cluster Count` remains the exact generated cluster count.
- `Branch Card Length` ranges from `0.5x` to `3.0x` and defaults to `1.5x`.
- `Length Variation` ranges from `0%` to `50%` and defaults to `0%`.
- A zero variation value is off; no separate toggle is added.
- `Card Scale` continues to control the base card size and width.
- `Branch Spacing` remains an independent placement control.

## Placement Contract

Foliage generation groups complete-graph anchors by stable branch ID. A foliage-bearing secondary
branch is a non-trunk branch at hierarchy depth two or greater with an explicit progress-zero
connection anchor and at least one eligible outer anchor.

Candidates on every qualifying branch run from the connection point toward the tip. The first
candidate is the progress-zero connection anchor. Additional requested clusters advance outward
along that branch. Retained physical secondary branches are selected before branches omitted from
the optimized wood, preserving the established physical-first rule.

Branch order, candidate order, and exact-count fallback remain deterministic and independent of the
requested count. Raising cluster count preserves the lower-count placement prefix.

## Geometry Contract

The exact top-right UV corner remains the attachment point. Generated transforms scale the source
card uniformly by `Card Scale`, then apply `Branch Card Length` only along the authored
attachment-to-center longitudinal axis. Width and plane separation are not lengthened.

Both planes in one shallow-V cluster always receive the same effective length. Length variation is
deterministic from `Foliage Seed` and cluster identity. It changes geometry only: it must not change
branch selection, anchor selection, template slot selection, rotation, or count.

For a base length `L` and variation `V`, the effective multiplier is sampled deterministically from
`L * (1 - V)` through `L * (1 + V)`. With the approved maximum `V = 0.5`, a `1.5x` base produces
values from `0.75x` through `2.25x`.

## Failure Handling

- Invalid or non-finite length and variation values fail before replacing existing foliage.
- A tree without qualifying secondary-branch connections fails explicitly instead of silently
  returning to tip-first placement.
- Existing trees with valid complete-graph anchors and retained-branch metadata can refresh without
  regenerating wood.

## Validation

- Unit tests prove secondary connection anchors precede outward candidates.
- Unit tests prove retained branches precede omitted branches and count increases preserve prefixes.
- Unit tests prove base length affects only longitudinal geometry inputs.
- Unit tests prove zero variation is uniform and non-zero variation is deterministic and bounded.
- Blender integration proves both planes share one length, attachment corners remain pinned, exact
  counts remain correct, and output metadata records both controls.

## Non-Goals

- Automatic cluster-count reduction or maximum-budget semantics.
- Per-branch automatic fitting.
- Changing the atlas layout, top-right attachment convention, or two-plane shallow-V format.
- Roblox runtime generation or foliage LOD generation.

