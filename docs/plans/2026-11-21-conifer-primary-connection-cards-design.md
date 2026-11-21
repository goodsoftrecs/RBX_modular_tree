# Conifer Primary-Connection Foliage Cards Design

## Purpose

Represent conifer limbs with long foliage cards beginning where primary branches meet the trunk,
without requiring many small secondary cards. Preserve the secondary-connection system for canopy
detail and broadleaf behavior.

## Controls and Defaults

- Add `Branch Start Layers` with `Secondary Only` and `Primary + Secondary`.
- Pine, Cedar, Sequoia, and Hemlock default to `Primary + Secondary`.
- Other species default to `Secondary Only`.
- Add `Primary Card Length`, range `0.5x` to `4.0x`, default `2.0x`.
- Secondary cards continue using `Branch Card Length`.
- Both layers share `Length Variation`; zero remains off.
- Every control is stored per tree and remains artist-overridable.

## Exact Placement Order

The exact requested cluster count is filled in this stable order:

1. qualifying primary progress-zero trunk connections;
2. qualifying secondary progress-zero branch connections;
3. remaining outward anchors on retained physical branches;
4. remaining outward anchors on branches omitted from optimized wood;
5. deterministic repetition only after selectable unique anchors are exhausted.

Within each connection layer, retained branches precede omitted branches. A qualifying branch has a
progress-zero connection anchor and at least one outward anchor. Count increases preserve the lower
count output as an exact prefix.

## Geometry

Primary placements use `Primary Card Length`; secondary placements use `Branch Card Length`.
Length remains longitudinal-only around the pinned top-right attachment corner. Both planes in a
cluster share the same deterministic varied length.

## Existing Trees

Newly generated trees receive their species default explicitly. Existing trees that have never set
`Branch Start Layers` receive their species default on first refresh. Once the artist changes the
control, refresh never overwrites it.

## Validation

- Pure tests prove primary connections precede secondary connections and outward anchors.
- Pure tests prove secondary-only mode excludes hierarchy-depth-one anchors.
- Pure tests prove primary and secondary length controls are independent.
- Blender integration proves conifer defaults, broadleaf defaults, metadata, UI ranges, and exact
  output counts.

