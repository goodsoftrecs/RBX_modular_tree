# Progressive Foliage Branch Fill Implementation Plan

## Purpose

Change foliage density from globally tip-biased reselection to cumulative branch-aware filling.

## Scope

- `python_classes/foliage_card_layout.py`
- `tests/unit/test_foliage_card_layout.py`
- `tests/blender/validate_foliage_cards.py`
- `README.md`

Native anchor extraction and atlas attachment geometry are unchanged.

## Non-Goals

- Adding another sidebar control.
- Changing physical-before-omitted priority.
- Changing the fixed shallow-V angle or atlas selection contract.

## Preconditions

- Progress-zero junction anchors from anchor payload schema 2 are available for regenerated trees.
- Existing schema-1 trees continue to fail closed and require regeneration.

## Implementation Slices

### 1. Branch-Layer Selection

Group physical anchors by branch, sort each branch tip-to-trunk, deterministically order branches,
and consume them round-robin by progress layer. Preserve the existing omitted-branch ascending
round-robin.

Acceptance: physical progress descends within layers and omitted progress ascends from zero.

### 2. Stable Random Streams

Separate selection ordering randomness from generated card appearance randomness.

Acceptance: every placement produced at count N is identical to the first N placements at count M
when M is greater than N.

### 3. Count-Independent Scale

Calculate automatic scale against a constant 30-cluster reference rather than requested count.

Acceptance: raising only Cluster Count does not change scale on existing placements.

### 4. Regression And Integration Coverage

Add pure tests for branch direction, stable prefixes, fixed scale, exact counts, and omitted-branch
ordering. Extend Blender validation to compare a lower-count generation against the prefix of a
higher-count refresh.

Acceptance: syntax, pure regression checks, package checks, and Blender validation pass when the
Windows bridge is available.

## Risks

- Trees with many retained physical branch IDs may spend the first layer on coverage before adding
  a second inward layer; this is intentional round-robin behavior.
- Old trees lack junction anchors and must be regenerated under schema 2.

## Doc Sync

Update the README Foliage Cards section to define progressive count behavior and count-independent
automatic scale.

