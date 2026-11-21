# Retained-Branch Progressive Foliage Spacing Design

## Goal

Make increasing `Foliage Cluster Count` extend foliage coverage along real generated limbs instead
of layering large card pairs around densely packed procedural tips.

## Confirmed Failure

`Pine_2` contains exactly 256 card-pair clusters, but their median nearest-center distance is only
about 0.24 Blender units while the median card diagonal is about 1.59 units. The result is roughly
48 connected visual foliage masses rather than 256 distinguishable placements.

The current physical-branch classifier also infers retained branches from proximity to any final
wood surface. On `Pine_2`, 198 branch IDs were treated as physical while only 119 graph tips matched
actual final-mesh terminal rings. Dense neighboring branches therefore create false-positive
physical classifications.

## Native Retained-Branch Contract

The manifold mesher will report the stable branch IDs it actually retained while applying its real
`max_branch_depth` and `minimum_branch_radius_ratio` decisions. Branch identity must use the same
complete-graph traversal contract as foliage-anchor extraction so retained IDs and anchor IDs cannot
drift.

Python will store the retained-ID report with the generated wood's foliage metadata. Foliage refresh
will consume that authoritative report. The BVH proximity classifier will not be the normal source
of physical-versus-omitted truth for newly generated trees.

Trees lacking the new retained-ID metadata must fail with a clear regeneration instruction rather
than silently returning to the disproven proximity guess.

## Progressive Placement Contract

Retained physical branches and omitted branches keep separate traversal directions:

- retained branch candidates run from tip toward trunk;
- omitted branch candidates run from their connection point toward their tip.

Selection uses deterministic per-branch cursors and a card-footprint-relative spacing target. When
a branch's next candidate is too close to an already accepted cluster, the cursor continues farther
along that same branch until it finds a sufficiently separated candidate. It does not accept the
overlapping candidate merely to give every raw branch ID one tip placement.

Branches are visited in deterministic rounds. When the cursor scans past candidates to find a
well-spaced location, it consumes the skipped prefix permanently. Later tighter-spacing phases may
use only candidates still ahead of that cursor; they must never backtrack toward a retained tip or
an omitted branch junction. The exact requested count is preserved by continuing into the other
branch class and, only after selectable unique locations are exhausted, deterministic repetition.

The complete selection sequence must be independent of the requested count. Raising a tree from 256
to 500 clusters therefore preserves the original 256 placements as an exact prefix and appends new
placements.

## Branch Spacing Control

Expose `Branch Spacing` as a per-tree multiplier:

- range: `0.1x` to `3.0x`;
- default: `1.0x`;
- basis: the generated card footprint after automatic sizing and `Card Scale`;
- lower values allow denser longitudinal placement;
- higher values skip farther along a branch before accepting another cluster;
- applies to retained tip-to-trunk traversal and omitted junction-to-tip traversal.

Changing `Card Scale` changes the automatic spacing distance proportionally. Artists can counteract
that relationship explicitly with `Branch Spacing`.

## Cluster Count Ceiling

Raise the authoring maximum from 256 to 512 so 500-cluster experiments are possible. Existing tree
defaults remain unchanged. One cluster remains two card planes and four triangles, so 500 clusters
produce 1,000 planes and approximately 2,000 foliage triangles.

## Failure Handling

- Missing or malformed retained-ID metadata fails before replacing existing foliage.
- Retained IDs absent from the anchor payload fail explicitly as a native contract mismatch.
- Invalid or non-finite spacing values fail validation.
- If the requested count exceeds distinct candidates, deterministic later phases may tighten spacing;
  exact anchor repetition remains a last resort only after all unique eligible anchors are exhausted.

## Validation

- Native tests prove retained IDs exactly follow depth and radius pruning.
- Python tests prove retained IDs, not BVH proximity, partition physical and omitted anchors.
- Higher counts preserve earlier placements as an exact prefix.
- Nearby tips cause traversal farther down a branch instead of immediate overlapping acceptance.
- `Branch Spacing` changes accepted longitudinal separation predictably and remains deterministic.
- Omitted branches still start at their connection points and progress outward.
- 500 clusters produce exactly 1,000 planes and approximately 2,000 foliage triangles.
- A regenerated `Pine_2` no longer reports more retained branch tips than the native mesher retained.

## Non-Goals

- Roblox runtime foliage generation.
- Automatic Roblox near/mid/far foliage LOD generation in this change.
- Changing the wood topology budget or species presets.
- Replacing the two-plane card-pair representation.
