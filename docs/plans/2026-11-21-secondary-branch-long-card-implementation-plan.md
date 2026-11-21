# Secondary-Branch Long Foliage Card Implementation Plan

## Purpose

Implement the approved connection-outward secondary-branch placement model and explicit
longitudinal card controls while preserving exact counts, deterministic output, and existing atlas
attachment behavior.

## Scope

- Pure placement selection and `CardPlacement` geometry inputs.
- Blender card transforms, properties, panel controls, and generated metadata.
- Unit and Blender integration tests.
- Add-on versioning, documentation, and packaging.

## Non-Goals

- Native anchor schema changes.
- Wood mesher changes.
- Automatic count reduction, LOD generation, or Roblox runtime changes.

## Preconditions

- Complete-graph anchors include progress-zero side-branch connection anchors.
- Native retained-branch IDs are stored on generated wood.
- The four-card atlas and top-right attachment convention remain authoritative.

## Implementation Slices

### 1. Add failing pure-layout tests

Files:

- `tests/unit/test_foliage_card_layout.py`

Work:

- Specify secondary-depth filtering, connection-first/outward traversal, physical-first ordering,
  stable prefixes, exact counts, and deterministic bounded length variation.

Acceptance:

- New tests fail against the current tip-first layout for the intended reasons.

### 2. Implement secondary-connection placement and length inputs

Files:

- `python_classes/foliage_card_layout.py`

Work:

- Select only foliage-bearing depth-two-or-greater branch groups with progress-zero anchors.
- Traverse retained and omitted qualifying branches connection-to-tip.
- Extend `CardPlacement` with one effective longitudinal multiplier shared by each card pair.
- Add validated base-length and variation inputs with independent deterministic RNG.

Acceptance:

- Pure tests pass; selection remains count-prefix-stable and exact.

### 3. Apply longitudinal-only transforms and expose controls

Files:

- `python_classes/foliage_cards.py`
- `python_classes/panels/__init__.py`

Work:

- Add `Branch Card Length` and `Length Variation` object properties.
- Pass them into layout generation.
- Scale only the authored long axis around the pinned attachment corner.
- Persist both values on generated foliage.

Acceptance:

- Width is unchanged by length; the top-right attachment remains pinned; both planes share length.

### 4. Extend Blender integration coverage

Files:

- `tests/blender/validate_foliage_cards.py`

Work:

- Validate property ranges/defaults, metadata, exact counts, deterministic variation, shared pair
  lengths, pinned corners, and longitudinal-only bounds.

Acceptance:

- The clean background Blender foliage validation passes.

### 5. Sync docs, version, and package

Files:

- `README.md`
- `VERSION`
- generated manifest/project versions and install archive

Work:

- Replace the old retained tip-to-trunk user workflow with secondary connection-outward behavior.
- Document both new controls and exact-count semantics.
- Build an offline Windows wheel and Blender extension ZIP.

Acceptance:

- Archive contains the new source, matching version metadata, and native wheel; installable package
  passes the existing clean Blender validation.

## Validation

- Pure Python unit suite.
- Python syntax compilation.
- Native tests as a regression check even though the native schema is unchanged.
- Clean Blender foliage integration test, including the existing 500-cluster geometry assertion.
- Package-content inspection.

## Risks

- A depth-two threshold can expose species-specific topology differences; fail explicitly if a tree
  has no qualifying secondary branches.
- Long cards can increase alpha overdraw even while reducing triangle count; Roblox forest profiling
  remains a later acceptance gate.
- Very high exact counts can still force dense or repeated placements after unique candidates are
  exhausted.

## Doc Sync

- Treat `2026-11-21-secondary-branch-long-card-design.md` as the controlling foliage placement
  contract.
- Retain earlier progressive-placement documents as historical context.
- Keep the `README.md` Foliage Cards workflow aligned with the new connection-outward model.

