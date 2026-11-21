# Trunk-Tip Foliage Pairs Implementation Plan

## Purpose

Add an artist-controlled terminal foliage pair at the conifer leader while preserving the existing
exact-count and pinned-card contracts.

## Scope

- Pure placement sequencing and per-cluster roll data.
- Per-tree Blender property, species defaults, migration, UI, and metadata.
- Unit and clean-Blender integration coverage.
- README, version, and offline package refresh.

## Non-Goals

- A separate apex length control.
- Changes to the four-tile atlas layout.
- Native mesher or retained-branch schema changes.
- Roblox runtime generation or LOD behavior.

## Preconditions

- Foliage anchors already identify hierarchy depth and normalized branch progress.
- Card geometry already supports a pinned top-right attachment and longitudinal length scaling.
- The requested cluster count remains the authoritative exact output count.

## Implementation Slices

1. Add failing pure tests for terminal selection, tip-first ordering, zero/two behavior, exact-count
   clamping, stable output, and the second pair's 90-degree roll.
   - Acceptance: tests describe the approved behavior and fail against 5.5.8.
   - Risk: terminal selection must remain deterministic when more than one depth-zero stem exists.
2. Extend the pure layout model with tip-pair reservation and per-cluster roll, then apply that roll
   during card-basis construction.
   - Acceptance: pure tests pass; existing placement ordering is unchanged after the reserved tips.
3. Add `Top Tip Pairs` with conifer/broadleaf defaults, first-refresh migration, UI wiring, and output
   metadata.
   - Acceptance: newly generated and legacy-unset trees resolve the correct species default while
     explicit artist values persist.
4. Extend clean Blender integration validation for property bounds, species defaults, metadata,
   exact object/triangle counts, and one-versus-two-pair orientation.
   - Acceptance: integration validation passes in a clean Blender process.
5. Update README and version, build the add-on offline, and inspect and test the archive.
   - Acceptance: the new installer contains the changed sources and passes the packaged validation.

## Validation

- Run the complete pure foliage-layout test file.
- Run native regression tests to confirm no mesher contract changed.
- Run clean Blender foliage-card and species-generation validation.
- Inspect the final archive contents and repeat relevant tests against its installed payload.

## Risks

- A zero-length terminal direction must fall back deterministically without producing invalid card
  geometry.
- The repeated apex anchor must carry a distinct roll without changing atlas selection or pinning.
- Property migration must distinguish an unset property from an artist-selected zero.

## Doc Sync

- Update `README.md` with the control, defaults, count semantics, and second-pair orientation.
- Bump `VERSION`; no server architecture documentation changes are required.

