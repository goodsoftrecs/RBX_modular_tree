# Foliage Card Corner Attachment Design

## Goal

Attach every generated foliage plane by the top-right UV corner of its atlas quadrant instead of
by the template object's origin or geometric middle. This matches the atlas authoring convention:
the branch connection pixel is always placed at the top-right of all four atlas regions.

## Placement Contract

- The exact `(maximum U, maximum V)` corner of the template's assigned quadrant is the attachment
  point.
- That point lands on the selected physical or virtual branch anchor.
- The direction from the attachment point to the card's geometric center aligns with the branch's
  outward foliage direction.
- Both planes in a shallow-V pair use the same atlas variant and attachment convention.
- Template object location remains library layout only; template rotation, scale, mesh edits, and
  UV edits remain authoring inputs.

The generator resolves the attachment point through mesh loop UVs. It does not assume that the
corner is a particular mesh vertex. If multiple loops reference the corner, their referenced vertex
positions are averaged. A template without the exact expected corner fails before existing valid
foliage is replaced.

## Branch Distance

Each generated tree receives a signed `Branch Distance` control:

- `0`: the top-right attachment point sits exactly on the branch anchor;
- positive: the plane moves away from the branch along that plane's perpendicular normal;
- negative: the plane moves into or through the branch along the opposite normal.

The two planes use their own normals, so a positive value opens the pair away from the branch on
both sides. The distance is a tree-space distance and is intentionally independent of Card Scale.

## Existing Controls

Card Scale, Texture Rotation, Card Pair Rotation, Canopy Rotation, cluster count, deterministic
variant selection, physical-branch priority, and missing-branch connection-outward filling remain
unchanged. Texture Rotation continues to transform generated UV sampling; the geometric attachment
point is determined from the unrotated authored quadrant corner.

## Validation

- For each of the four atlas slots, the authored top-right UV point maps exactly to the requested
  branch anchor at Branch Distance `0`.
- Positive and negative Branch Distance values move that point by the signed amount along the
  plane normal.
- The transformed card center lies in the generated placement direction from its attachment point.
- Invalid templates fail closed and preserve the last valid generated foliage object.
- Existing deterministic refresh and card-count guarantees continue to pass.

