# Conifer Primary-Connection Foliage Cards Implementation Plan

## Purpose

Add an artist-controlled primary foliage layer for conifers while retaining exact deterministic
counts and the existing secondary long-card system.

## Implementation Slices

1. Add failing pure tests for layer filtering, priority order, stable prefixes, and independent
   primary length.
2. Generalize candidate grouping to support depth-one primary and depth-two-or-greater secondary
   branches, then implement the approved connection and outward priority order.
3. Add per-tree `Branch Start Layers` and `Primary Card Length` properties, species defaults,
   migration-on-first-refresh, UI wiring, and output metadata.
4. Extend clean Blender integration tests for Oak and conifer defaults and geometry behavior.
5. Update the README, bump the version, build offline, and inspect/test the package.

## Non-Goals

- Automatic count reduction.
- Separate primary variation.
- Atlas or native anchor schema changes.
- Roblox runtime generation or LOD work.

## Acceptance

- Pine, Cedar, Sequoia, and Hemlock default to primary plus secondary cards.
- Broadleaf trees default to secondary-only cards.
- Exact count and prefix stability remain intact.
- Primary cards pin to trunk/branch connections and use their own length control.
- Unit, native regression, and clean Blender integration tests pass.

