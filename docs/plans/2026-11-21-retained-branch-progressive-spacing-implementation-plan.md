# Retained-Branch Progressive Foliage Spacing Implementation Plan

## Purpose

Replace proximity-inferred physical branches with an authoritative native retained-branch report,
then distribute card clusters progressively along those branches with artist-controlled spacing.

## Scope

- Shared stable native branch identity for anchor extraction and manifold meshing.
- Native reporting of branch IDs retained by the configured wood profile.
- Blender metadata storage and strict loading of the retained-ID report.
- Spatially aware deterministic branch traversal with a `Branch Spacing` multiplier.
- A 512-cluster authoring ceiling.
- Native, pure-Python, and Blender integration validation.

## Non-Goals

- Roblox runtime LOD generation.
- Species or wood-budget retuning.
- A different foliage-card mesh representation.
- Runtime camera-facing billboards.

## Preconditions

- Approved design: `2026-11-21-retained-branch-progressive-spacing-design.md`.
- Existing complete-graph foliage anchors and stable branch-progress values remain authoritative for
  placement candidates.
- The Windows native wheel must be rebuilt and the Blender extension reinstalled before live MCP
  validation can exercise the new native contract.

## Implementation Slices

### 1. Add shared native branch identity and retained-ID reporting

Purpose: ensure anchor IDs and mesher-retained IDs are generated from one complete-tree traversal.

Likely files:

- `m_tree/source/tree/FoliageAnchor.cpp`
- `m_tree/source/tree/FoliageAnchor.hpp`
- a new shared branch-identity utility under `m_tree/source/tree/`
- `m_tree/source/meshers/manifold_mesher/ManifoldMesher.hpp`
- `m_tree/source/meshers/manifold_mesher/ManifoldMesher.cpp`
- `m_tree/source/CMakeLists.txt`
- `m_tree/python_bindings/main.cpp`
- `m_tree/tests/main.cpp`

Work:

- Assign branch IDs across the full graph before pruning.
- Make anchor extraction consume that shared mapping.
- Record a branch ID only when the manifold mesher actually enters and emits that branch under its
  depth/radius settings.
- Clear the report on every mesh build and expose a read-only Python copy immediately after
  `mesh_tree()`.

Acceptance:

- Native tests prove full-detail settings retain all generated branch IDs.
- Depth/radius pruning reports exactly the expected retained subset while anchor IDs remain stable.
- Repeated mesh calls cannot leak retained IDs from a previous tree.

Risk:

- A retained-ID counter that advances only through meshed children would drift from complete-graph
  anchor IDs. The shared pre-pruning identity traversal is mandatory.

### 2. Persist and validate the native report in Blender metadata

Purpose: make foliage refresh use exact retained identity after the native tree object is gone.

Likely files:

- `python_classes/foliage_anchor_data.py`
- `python_classes/operators.py`
- `python_classes/nodes/tree_function_nodes/tree_mesher_node.py`
- `tests/unit/test_foliage_anchor_data.py`
- `tests/blender/validate_species_generation.py`

Work:

- Add a dedicated retained-branch-ID metadata key plus strict store/load helpers.
- Capture the mesher report in quick generation and node-editor generation.
- Store anchors and retained IDs together in the same generation transaction.
- Reject missing, malformed, duplicate, negative, or anchor-unknown retained IDs.
- Require regeneration for legacy trees without this metadata.

Acceptance:

- Both generation paths persist the same native report contract.
- Invalid metadata fails before existing foliage is replaced.
- Unit tests cover valid round-trip and every rejection path.

### 3. Replace proximity classification with authoritative partitioning

Purpose: remove the false-positive path demonstrated by `Pine_2`.

Likely files:

- `python_classes/foliage_cards.py`
- `python_classes/foliage_card_layout.py`
- `tests/unit/test_foliage_card_layout.py`
- `tests/blender/validate_foliage_cards.py`

Work:

- Partition eligible anchors by membership in the stored retained-ID set.
- Define omitted IDs as complete non-trunk branch IDs absent from the retained report.
- Remove the BVH proximity classifier from the normal foliage refresh path.
- Preserve physical-first and omitted connection-outward semantics.

Acceptance:

- A graph branch close to unrelated wood remains omitted when absent from the native report.
- Metadata counts on generated foliage match the authoritative retained/omitted partition.

### 4. Implement deterministic footprint-relative progressive spacing

Purpose: make added clusters extend coverage instead of creating dense endpoint piles.

Likely files:

- `python_classes/foliage_card_layout.py`
- `python_classes/foliage_cards.py`
- `tests/unit/test_foliage_card_layout.py`

Work:

- Compute a template footprint from the resolved card templates and generated card scale.
- Add `branch_spacing` and footprint inputs to layout validation.
- Traverse retained branch candidates tip-to-trunk with deterministic per-branch cursors.
- When a candidate violates current spacing, advance farther down that same branch and permanently
  consume the skipped prefix so later phases cannot reverse direction.
- Traverse omitted candidates junction-to-tip.
- Use fixed deterministic spacing phases only for candidates still ahead of each branch cursor.
- Make the selection order independent of requested count so higher counts are exact prefixes.
- Repeat anchors only after all unique candidates have been consumed.

Acceptance:

- Nearby branch tips do not both win the first well-spaced phase.
- The affected branch advances longitudinally to a separated candidate.
- Higher `Branch Spacing` yields greater early center separation.
- Counts 30, 256, and 500 are exact and deterministic.
- The first 256 placements of a 500-cluster layout exactly equal the standalone 256 layout.

Risk:

- Exact high counts may be impossible at the requested spacing. Deterministic later phases must
  tighten spacing without reordering earlier accepted placements.

### 5. Expose controls and metadata

Purpose: give artists direct control while preserving current defaults.

Likely files:

- `python_classes/foliage_cards.py`
- `python_classes/panels/__init__.py`
- `tests/blender/validate_foliage_cards.py`

Work:

- Add per-tree `Branch Spacing`, range `0.1` to `3.0`, default `1.0`.
- Display it with the existing foliage controls.
- Persist the value on generated foliage for inspection.
- Raise `Foliage Cluster Count` maximum from 256 to 512 without changing its default.

Acceptance:

- Existing trees receive the registered default when no explicit value was authored.
- Blender accepts 500 and rejects values above 512.
- Refresh metadata reports the effective spacing.

### 6. Build, package, and validate live

Purpose: prove source, wheel, extension package, and live Blender agree.

Likely files/tools:

- `build_mtree.bat`
- existing extension packaging workflow
- `tests/blender/validate_foliage_cards.py`
- live Blender MCP scene containing `Pine_2`

Work:

- Run pure Python and native tests before packaging.
- Rebuild the Windows native wheel using the repository batch workflow without downloading new
  dependencies.
- Reinstall/reload the extension as required by the existing workflow.
- Regenerate `Pine_2`, because legacy wood lacks authoritative retained-ID metadata.
- Compare retained-ID count, cluster count, nearest-center distribution, and longitudinal coverage.

Acceptance:

- Blender loads the rebuilt native module and exposes the retained-ID report.
- Regenerated `Pine_2` no longer uses BVH proximity classification.
- Increasing cluster count visibly adds placements down limbs.
- 500 clusters produce 1,000 planes and approximately 2,000 foliage triangles.

## Validation

- Native C++ tests for identity and pruning.
- Pure Python unit tests for metadata, partitioning, spacing, determinism, stable prefixes, and exact
  counts.
- Blender integration tests for property registration, generation paths, refresh replacement safety,
  and geometry counts.
- Live MCP measurement on regenerated `Pine_2`.

## Risks

- Existing generated trees must be regenerated once; silently guessing is intentionally disallowed.
- The native wheel and installed Blender extension can drift. Verify the loaded module path and new
  API before judging live output.
- Large card footprints and high counts inevitably require some overlap; the algorithm improves the
  order of coverage rather than promising 500 visually isolated cards inside a finite canopy.
- Five hundred clusters are about 2,000 foliage triangles per tree, but transparency overdraw still
  requires a later Roblox forest stress test and eventual LOD work.

## Doc Sync

- Keep `2026-11-20-progressive-foliage-branch-fill-design.md` as historical context.
- Treat `2026-11-21-retained-branch-progressive-spacing-design.md` as the controlling placement
  contract.
- Update the foliage handoff/status document if one is discovered during implementation.
