# Foliage Card Corner Attachment Implementation Plan

## 1. Resolve The Authored Attachment Frame

- Locate each slot's maximum-U/maximum-V loop in the active UV layer.
- Derive the attachment point, geometric-center direction, and mesh-plane normal after applying the
  template object's authored rotation and scale.
- Fail explicitly on missing UV corners or degenerate card geometry.

Acceptance: all four initialized templates produce a valid attachment frame without relying on a
hard-coded vertex index.

## 2. Generate Corner-Anchored Cards

- Replace the origin-based placement transform with a source-frame to target-frame transform.
- Map the top-right attachment point to the branch anchor.
- Align attachment-to-center with the placement direction.
- Apply Card Scale around the attachment point.

Acceptance: the attachment point remains fixed while template scale, rotation, and mesh shape affect
the rest of the generated card.

## 3. Add Signed Branch Distance

- Register the per-tree `mtree_foliage_branch_distance` property.
- Initialize it to zero on generated trees.
- Expose it in the Foliage Cards panel.
- Apply it independently along each plane's placement normal and record it on generated foliage.

Acceptance: positive and negative values produce equal and opposite perpendicular offsets without
changing cluster count or atlas selection.

## 4. Verify And Document

- Extend Blender integration validation with exact transform assertions and property checks.
- Verify failure preservation for a template missing its required top-right corner.
- Update the README workflow and control description.
- Run available unit checks, syntax compilation, add-on packaging, and Blender integration when the
  local Blender bridge is available.

