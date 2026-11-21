# Progressive Foliage Branch Fill Design

## Goal

Make `Foliage Cluster Count` visibly add foliage along branches instead of repeatedly favoring
widely separated tips while shrinking every card. Increasing the count must preserve all earlier
placements and append additional clusters deterministically.

## Distribution Contract

Eligible anchors are grouped by procedural `branch_id`.

- Physical branches retain priority over omitted branches.
- Physical branch anchors are ordered from tip to trunk by descending `branch_progress`.
- Physical branches are consumed in deterministic round-robin layers: one tip anchor per branch,
  then the next inward anchor per branch, continuing toward the trunk.
- Omitted branches retain the inverse safety rule: their progress-zero junction anchor is consumed
  first, followed by anchors moving outward toward the tip.
- The selection sequence is a stable prefix. For the same tree and seed, the first 30 clusters at a
  count of 60 are identical to the complete result generated at a count of 30.

Physical branch ordering remains deterministic and favors strong outer foliage candidates, but
selection no longer uses a global farthest-point pass over every anchor. Random streams for anchor
ordering and card appearance are separated so crossing from physical into omitted branches cannot
rotate or rescale previously generated cards.

## Scale Contract

Automatic base scale is derived using a fixed reference density of 30 clusters. Cluster Count no
longer participates in the scale formula. Raising the count therefore adds density; it does not
shrink all existing cards. `Card Scale` remains the explicit user control for overall card size.

## Validation

- Requested cluster count still produces exactly twice as many card planes.
- Raising count preserves previous anchor indices, positions, directions, normals, scales, and
  atlas slots as an exact prefix.
- Physical anchors progress tip-to-trunk within each branch layer.
- Omitted anchors progress junction-to-tip.
- Card scale is identical for the same tree and Card Scale setting regardless of Cluster Count.

