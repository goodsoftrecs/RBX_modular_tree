# Canopy Lobes Implementation Plan

## Purpose

Implement the approved deterministic, selection-driven canopy-lobe authoring workflow in the RBX
Modular Tree Blender add-on.

## Scope

- Editable low-poly lobe-template creation.
- Structured generated-tree collections and ownership metadata.
- Deterministic lobe placement from retained wood mesh attributes.
- One combined foliage mesh per tree.
- Per-tree lobe count, scale, and canopy seed controls.
- Generate/refresh behavior from the active wood or foliage object.

## Non-Goals

- Final alpha foliage texture and Roblox `SurfaceAppearance` setup.
- Wind deformation or runtime animation.
- Removal of upstream leaf-generation controls.
- Automatic canopy generation during quick tree generation.

## Preconditions

- Wood meshes retain the current MTree point attributes.
- The existing quick generator continues to provide a numeric generation seed.
- Canopy templates use one shared preview material in the first slice.

## Implementation Slices

### 1. Add deterministic layout primitives

Purpose: isolate placement decisions from Blender data access.

Likely files:

- `python_classes/canopy_layout.py`
- `tests/unit/test_canopy_layout.py`

Work:

- Define branch-anchor and lobe-placement data structures.
- Add deterministic, spatially distributed anchor selection.
- Add template classification and crown-relative base-scale calculation.

Acceptance: fixed candidates, seed, count, and scale reproduce identical placements; changing the
seed can change tie-breaking while preserving the requested count.

Risk: clustered branches can produce visually redundant anchors; use distance-aware selection and
explicit fallback behavior.

### 2. Add lobe-template authoring resources

Purpose: create editable starting shapes without manual modeling.

Likely files:

- `python_classes/canopy_lobes.py`
- `tests/blender/validate_canopy_lobes.py`

Work:

- Create `MTree_CanopyLibrary`.
- Generate round, wide, and tip meshes with UVs and approximately 30-60 triangles each.
- Assign a shared green preview material.
- Create only missing templates; preserve existing objects and edits.

Acceptance: the button creates all three named, tagged, editable templates and a second invocation
does not replace their mesh data.

Risk: UV seams on closed lobes must remain valid for the later alpha texture even though the first
material is opaque.

### 3. Add tree ownership and scene organization

Purpose: make selected-tree refresh reliable and keep templates separate from outputs.

Likely files:

- `python_classes/canopy_lobes.py`
- `python_classes/operators.py`

Work:

- Add stable tree IDs and object-role metadata.
- Organize new quick-generated trees under `MTree_GeneratedTrees/Tree_<seed>` with root, wood, and
  foliage naming.
- Adopt legacy `Tree_<number>` wood objects on first refresh.
- Resolve an active wood or foliage object to its owning wood object and collection.

Acceptance: selection of either role resolves the same tree; unrelated meshes fail with a clear
operator error and are not reorganized.

Risk: legacy adoption must not unlink the wood object from every visible collection before the new
collection is safely linked.

### 4. Generate and refresh combined foliage

Purpose: turn branch metadata and templates into one export-friendly foliage mesh.

Likely files:

- `python_classes/canopy_lobes.py`
- `python_classes/canopy_layout.py`
- `tests/blender/validate_canopy_lobes.py`

Work:

- Extract one endpoint candidate per retained stem from mesh attributes.
- Resolve exact deterministic placements.
- Transform and combine template vertices, faces, and UV loops into one foliage mesh.
- Replace only the prior foliage object while preserving its owner, settings, and seed.

Acceptance: refresh produces the requested number of lobes in one mesh; identical inputs reproduce
identical geometry; template resizing changes refreshed geometry; wood remains byte-for-byte
unchanged.

Risk: missing or malformed wood attributes must fail explicitly without deleting existing foliage.

### 5. Add sidebar controls and operators

Purpose: expose the approved workflow without requiring collection or template selection.

Likely files:

- `python_classes/operators.py`
- `python_classes/panels/__init__.py`
- `python_classes/__init__.py`

Work:

- Register per-tree canopy settings.
- Add `Create Canopy Lobes` and `Generate / Refresh Lobes` operators.
- Draw lobe count, scale, and seed from the resolved active tree.
- Default canopy seed to the quick-generation seed.

Acceptance: selecting wood or foliage shows the same saved settings and Refresh operates on that
tree without manual collection selection.

Risk: Blender registration/unregistration must cleanly handle property definitions during add-on
reloads.

### 6. Package and regression-test the add-on

Purpose: deliver a reinstallable build without regressing the ~3K wood profile.

Likely files:

- `README.md`
- packaged output under `tmp/`

Work:

- Document the canopy workflow and preview-material limitation.
- Run unit tests, the wood-profile Blender test, and the canopy Blender integration test.
- Build and inspect the extension archive.

Acceptance: all existing tests pass, canopy integration passes in Blender 4.4, and the packaged ZIP
contains the new modules and UI.

## Validation

- `python -m pytest unit -q` from `tests/`.
- Blender background validation for wood output.
- Blender background validation for template creation, collection structure, deterministic refresh,
  legacy adoption, and template-resize propagation.
- Archive manifest parse and archive-content inspection.

## Risks

- The current mesh attributes may not provide enough unique stems for extremely sparse custom
  node trees; fallback placement must remain deterministic and explicit.
- A later alpha texture may require UV adjustments, but it must not require replacing the ownership
  or refresh architecture.
- Joined foliage is intentionally generated output; direct edits to it are replaced on Refresh.

## Doc Sync

- Keep `docs/plans/2026-11-17-canopy-lobes-design.md` authoritative for this feature.
- Update `README.md` once implementation behavior is validated.

