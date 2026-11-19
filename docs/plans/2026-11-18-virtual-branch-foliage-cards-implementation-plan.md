# Virtual Branch Foliage Cards Implementation Plan

## Purpose

Implement the approved virtual-branch foliage-card workflow in the RBX Modular Tree Blender add-on.
The final tree keeps optimized wood while card placement uses anchors extracted from the complete MTree
branch graph before mesh pruning.

## Scope

- C++ traversal of the complete tree graph into deterministic foliage-anchor records.
- Python binding for anchor extraction.
- Persistent Blender-only anchor metadata on generated wood objects.
- One editable foliage-card template.
- Deterministic weighted anchor selection and shallow-V placement.
- One combined foliage mesh per tree.
- Sidebar controls and safe refresh behavior.
- Unit, native, and Blender integration validation.
- Add-on package rebuild after validation.

## Non-Goals

- Texture-atlas region distribution.
- Runtime camera-facing billboards.
- Wind, skeletal, or shader animation.
- Roblox-side code changes.
- Automatic tree LOD generation.
- Removal of the existing canopy-lobe source during the prototype.

## Preconditions

- The optimized `ManifoldMesher` continues to prune only while constructing geometry.
- Tree generation seed and preset remain available at generation time.
- Existing artist content under `PNGs/` is not modified.
- The existing tree ownership and collection structure remains authoritative.

## Implementation Slices

### 1. Add complete-graph foliage-anchor extraction

Purpose: expose lightweight placement data without generating a full wood mesh.

Likely files:

- `m_tree/source/tree/`
- `m_tree/python_bindings/main.cpp`
- `m_tree/tests/main.cpp`

Work:

- Define a compact anchor record with position, direction, radius, depth, branch identity, and branch
  progress.
- Traverse every stem and side branch in stable order using the same position rules as the mesher.
- Expose anchor extraction through the Python extension.
- Keep extraction independent from `ManifoldMesher` pruning settings.

Acceptance:

- Same generated tree returns byte-for-byte equivalent ordered anchor values.
- Optimized mesh pruning does not reduce the extracted anchor set.
- Native tests prove that anchors exist at depths omitted from optimized wood.

Risk: position traversal must match MTree child placement semantics, especially side-branch offsets.

### 2. Persist anchor metadata during Blender tree generation

Purpose: make refresh deterministic after reopening a `.blend` without adding exportable objects.

Likely files:

- `python_classes/operators.py`
- new `python_classes/foliage_anchor_data.py`
- unit tests under `tests/unit/`

Work:

- Extract anchors before calling the optimized mesher.
- Serialize a versioned, validated payload onto the organized wood object.
- Save generation preset alongside the existing generation seed for diagnostics.
- Decode with explicit schema and finite-number validation.

Acceptance:

- A newly generated tree contains a valid versioned anchor payload.
- Round-trip encode/decode preserves ordered anchor records.
- No anchor object appears in the export collection.

Risk: Blender ID-property types require a compact representation that remains stable across save/load.

### 3. Add pure deterministic card layout

Purpose: select useful anchors and compute shallow-V card transforms without Blender dependencies.

Likely files:

- new `python_classes/foliage_card_layout.py`
- new `tests/unit/test_foliage_card_layout.py`

Work:

- Exclude trunk, thick interior, and invalid anchors.
- Weight outer, small-radius, deeper anchors while retaining spatial coverage.
- Select the exact requested cluster count deterministically, repeating eligible anchors only when
  necessary.
- Produce two transforms per cluster with a fixed shallow-V angle and branch-aligned long axes.
- Derive base scale from crown dimensions and cluster count, then apply the user multiplier.

Acceptance:

- Same inputs produce identical transforms.
- Cluster count is exact and card count is exactly double.
- Pair normals form the configured fixed V angle.
- Trunk and deliberately oversized interior anchors are excluded.

Risk: over-weighting branch depth can create a hollow or top-heavy crown; tests must cover spatial
distribution as well as filtering.

### 4. Add editable template and combined foliage output

Purpose: create artist-controlled source geometry and safe per-tree outputs.

Likely files:

- new `python_classes/foliage_cards.py`
- `python_classes/__init__.py`
- `python_classes/operators.py`
- `python_classes/canopy_lobes.py` for shared ownership helpers only if a clean extraction is useful
- `tests/blender/validate_foliage_cards.py`

Work:

- Create `MTree_FoliageLibrary/FoliageCard_Template` only when missing.
- Give the template one quad, full `0-1` UVs, and a shared preview material.
- Copy template vertices, faces, UVs, and material assignment through each card transform.
- Build and link new foliage before removing old foliage.
- Preserve existing tree root, wood object, IDs, seed, and collection.

Acceptance:

- Template initialization is idempotent and preserves artist edits.
- Thirty clusters create 60 cards and approximately 120 triangles in one mesh.
- Refresh from selected wood or selected foliage resolves the same owner.
- Template edits appear after refresh.
- A failed refresh preserves old foliage.

Risk: card local axes must be explicit so artist edits do not unexpectedly change branch alignment.

### 5. Replace the primary sidebar workflow

Purpose: make the new system usable without exposing implementation details.

Likely files:

- `python_classes/panels/__init__.py`
- `python_classes/operators.py`
- `python_classes/__init__.py`

Work:

- Add `Create Foliage Card Template`.
- Add per-tree `Foliage Cluster Count`, `Card Scale`, and `Foliage Seed` properties.
- Add `Generate / Refresh Foliage Cards`.
- Initialize seed from the tree seed and use a 30-cluster default.
- Remove canopy lobes from the primary visible workflow while leaving their implementation intact.
- Report legacy trees without dense anchors clearly and direct the user to regenerate them.

Acceptance:

- A new tree can create its template and foliage from the sidebar without manual custom properties.
- Controls remain available when either wood or foliage is selected.
- Legacy trees fail with a concise actionable message rather than generating endpoint-only foliage.

### 6. Validate and package

Purpose: prove the system and hand off a Blender-installable build.

Likely files:

- `m_tree/tests/main.cpp`
- `tests/unit/`
- `tests/blender/validate_foliage_cards.py`
- `README.md`
- add-on package under `tmp/`

Work:

- Run native C++ tests after rebuilding the extension.
- Run Python unit tests.
- Run Blender 4.4 integration validation against source and the packaged add-on.
- Confirm representative optimized wood triangle counts remain in their established range.
- Update the README with the new card workflow and atlas-later boundary.
- Build the installation ZIP without including `PNGs/` or other user content.

Acceptance:

- All native, unit, and Blender integration tests pass.
- Optimized wood regression checks pass.
- Packaged add-on creates a tree with persistent anchors and refreshable shallow-V foliage cards.
- `git diff --check` is clean.

### 7. Add per-tree foliage appearance rotations

Purpose: provide direct appearance control without shader-node authoring or per-tree material copies.

Likely files:

- `python_classes/foliage_card_layout.py`
- `python_classes/foliage_cards.py`
- `python_classes/canopy_lobes.py`
- `python_classes/panels/__init__.py`
- `tests/unit/test_foliage_card_layout.py`
- `tests/blender/validate_foliage_cards.py`

Work:

- Raise the Card Scale upper bound from `4x` to `12x`.
- Add per-tree texture, card-pair, and canopy rotation properties shown as degree controls.
- Rotate UVs around their center with an inverse sampling scale that fits the complete image inside
  the card, and use one tree-owned clipped material copy when texture rotation is nonzero.
- Apply card-pair rotation as a roll around each selected branch direction while preserving the fixed
  shallow-V angle.
- Apply canopy rotation to positions, directions, and normals around the tree-local Z axis.
- Persist the applied controls on the generated foliage object for inspection.

Acceptance:

- Zero rotation preserves existing deterministic output.
- Rotated UVs and clipped sampling show the complete image without Repeat wrapping.
- Pair rotation changes card orientation without changing anchor selection, scale, or V angle.
- Canopy rotation changes the complete placement set around the local origin.
- Repeated refresh with identical controls remains deterministic.

Risk: rotating texture coordinates without fitting would crop or wrap texture corners; the fit factor
is therefore part of the control contract rather than an optional shader behavior.

## Validation Summary

- Native: complete graph traversal and pruning independence.
- Pure Python: payload schema, anchor filtering, deterministic layout, exact card counts, V angle.
- Blender: template lifecycle, ownership, safe replacement, UV/material preservation, persistence.
- Packaging: clean install and smoke generation in Blender 4.4.
- Performance follow-up: profile 50-70 placed tree instances in Roblox before expanding atlas density or
  adding LOD behavior.

## Risks

- Dense anchors may produce excessive visual overlap unless filtering favors spatial separation.
- Alpha-card performance is dominated by screen-space overdraw rather than triangle count.
- Existing trees lack the complete anchor payload and need regeneration.
- Rebuilding the compiled extension requires Blender/Python 3.11-compatible output and may be blocked
  while Blender has the installed `.pyd` loaded.
- Material preview behavior in Blender does not prove Roblox transparency performance.

## Doc Sync

- Keep `docs/plans/2026-11-18-virtual-branch-foliage-cards-design.md` authoritative for the feature.
- Update `README.md` when implementation is complete.
- The prior canopy-lobes design remains historical context and must not be rewritten as if cards were
  its original design.
