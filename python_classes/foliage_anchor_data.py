"""Versioned persistence for foliage anchors extracted from MTree's full graph."""

from __future__ import annotations

import base64
import json
import math
import zlib
from dataclasses import dataclass
from typing import Iterable


ANCHOR_PAYLOAD_KEY = "mtree_foliage_anchor_payload"
RETAINED_BRANCH_IDS_KEY = "mtree_foliage_retained_branch_ids"
ANCHOR_PAYLOAD_SCHEMA = 2
_PAYLOAD_PREFIX = "zlib-json-v1:"
_MAX_ANCHORS = 250_000


@dataclass(frozen=True)
class FoliageAnchor:
    """Minimal tree-local placement data retained after optimized wood meshing."""

    position: tuple[float, float, float]
    direction: tuple[float, float, float]
    radius: float
    hierarchy_depth: int
    branch_id: int
    branch_progress: float


def _finite_vector(value: object, field_name: str) -> tuple[float, float, float]:
    try:
        result = tuple(float(component) for component in value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Foliage anchor {field_name} must contain three numbers") from exc
    if len(result) != 3 or not all(math.isfinite(component) for component in result):
        raise ValueError(f"Foliage anchor {field_name} must contain three finite numbers")
    return result


def validate_anchor(anchor: FoliageAnchor) -> FoliageAnchor:
    position = _finite_vector(anchor.position, "position")
    direction = _finite_vector(anchor.direction, "direction")
    radius = float(anchor.radius)
    progress = float(anchor.branch_progress)
    depth = int(anchor.hierarchy_depth)
    branch_id = int(anchor.branch_id)

    if not math.isfinite(radius) or radius < 0.0:
        raise ValueError("Foliage anchor radius must be finite and non-negative")
    if not math.isfinite(progress) or not 0.0 <= progress <= 1.0:
        raise ValueError("Foliage anchor branch progress must be between zero and one")
    if depth < 0 or branch_id < 0:
        raise ValueError("Foliage anchor depth and branch id must be non-negative")
    if sum(component * component for component in direction) <= 1e-12:
        raise ValueError("Foliage anchor direction must be non-zero")

    return FoliageAnchor(position, direction, radius, depth, branch_id, progress)


def anchors_from_native(native_anchors: Iterable[object]) -> list[FoliageAnchor]:
    """Copy pybind anchor objects while their native tree still exists."""

    anchors = [
        validate_anchor(
            FoliageAnchor(
                position=_finite_vector(anchor.position, "position"),
                direction=_finite_vector(anchor.direction, "direction"),
                radius=float(anchor.radius),
                hierarchy_depth=int(anchor.hierarchy_depth),
                branch_id=int(anchor.branch_id),
                branch_progress=float(anchor.branch_progress),
            )
        )
        for anchor in native_anchors
    ]
    if not anchors:
        raise ValueError("MTree's complete graph produced no foliage anchors")
    if len(anchors) > _MAX_ANCHORS:
        raise ValueError(f"Foliage anchor count exceeds {_MAX_ANCHORS}")
    return anchors


def encode_anchor_payload(anchors: Iterable[FoliageAnchor]) -> str:
    validated = [validate_anchor(anchor) for anchor in anchors]
    if not validated:
        raise ValueError("At least one foliage anchor is required")
    if len(validated) > _MAX_ANCHORS:
        raise ValueError(f"Foliage anchor count exceeds {_MAX_ANCHORS}")

    rows = [
        [
            *anchor.position,
            *anchor.direction,
            anchor.radius,
            anchor.hierarchy_depth,
            anchor.branch_id,
            anchor.branch_progress,
        ]
        for anchor in validated
    ]
    raw = json.dumps(
        {"schemaVersion": ANCHOR_PAYLOAD_SCHEMA, "anchors": rows},
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return _PAYLOAD_PREFIX + base64.b64encode(zlib.compress(raw, level=9)).decode("ascii")


def decode_anchor_payload(payload: object) -> list[FoliageAnchor]:
    if not isinstance(payload, str) or not payload.startswith(_PAYLOAD_PREFIX):
        raise ValueError("Foliage anchor payload has an unsupported encoding")
    try:
        compressed = base64.b64decode(payload[len(_PAYLOAD_PREFIX) :], validate=True)
        document = json.loads(zlib.decompress(compressed).decode("utf-8"))
    except (ValueError, TypeError, zlib.error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Foliage anchor payload is corrupt") from exc

    if not isinstance(document, dict) or document.get("schemaVersion") != ANCHOR_PAYLOAD_SCHEMA:
        raise ValueError("Foliage anchor payload uses an unsupported schema")
    rows = document.get("anchors")
    if not isinstance(rows, list) or not rows or len(rows) > _MAX_ANCHORS:
        raise ValueError("Foliage anchor payload has an invalid anchor count")

    anchors: list[FoliageAnchor] = []
    for row in rows:
        if not isinstance(row, list) or len(row) != 10:
            raise ValueError("Foliage anchor payload contains a malformed row")
        anchors.append(
            validate_anchor(
                FoliageAnchor(
                    position=(row[0], row[1], row[2]),
                    direction=(row[3], row[4], row[5]),
                    radius=row[6],
                    hierarchy_depth=row[7],
                    branch_id=row[8],
                    branch_progress=row[9],
                )
            )
        )
    return anchors


def store_anchor_payload(wood: object, anchors: Iterable[FoliageAnchor]) -> None:
    wood[ANCHOR_PAYLOAD_KEY] = encode_anchor_payload(anchors)  # type: ignore[index]


def validate_retained_branch_ids(
    retained_branch_ids: Iterable[object], anchors: Iterable[FoliageAnchor]
) -> frozenset[int]:
    """Validate the native mesher's retained IDs against the complete anchor graph."""

    anchor_ids = {validate_anchor(anchor).branch_id for anchor in anchors}
    try:
        raw_ids = list(retained_branch_ids)
    except TypeError as exc:
        raise ValueError("Retained branch IDs must be an iterable of integers") from exc
    if not raw_ids:
        raise ValueError("Native mesher reported no retained branch IDs")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in raw_ids):
        raise ValueError("Retained branch IDs must contain only integers")
    normalized = [int(value) for value in raw_ids]
    if any(value < 0 for value in normalized):
        raise ValueError("Retained branch IDs must be non-negative")
    if len(set(normalized)) != len(normalized):
        raise ValueError("Retained branch IDs must not contain duplicates")
    unknown = set(normalized) - anchor_ids
    if unknown:
        raise ValueError("Native mesher reported branch IDs absent from foliage anchors")
    return frozenset(normalized)


def store_retained_branch_ids(
    wood: object,
    retained_branch_ids: Iterable[object],
    anchors: Iterable[FoliageAnchor],
) -> None:
    validated = validate_retained_branch_ids(retained_branch_ids, anchors)
    wood[RETAINED_BRANCH_IDS_KEY] = sorted(validated)  # type: ignore[index]


def load_anchor_payload(wood: object) -> list[FoliageAnchor]:
    try:
        payload = wood.get(ANCHOR_PAYLOAD_KEY)  # type: ignore[attr-defined]
    except AttributeError as exc:
        raise ValueError("Selected object cannot store foliage anchor metadata") from exc
    if payload is None:
        raise ValueError(
            "Tree has no complete-graph foliage anchors; regenerate it with this MTree version"
        )
    return decode_anchor_payload(payload)


def load_retained_branch_ids(
    wood: object, anchors: Iterable[FoliageAnchor]
) -> frozenset[int]:
    try:
        retained_branch_ids = wood.get(RETAINED_BRANCH_IDS_KEY)  # type: ignore[attr-defined]
    except AttributeError as exc:
        raise ValueError("Selected object cannot store foliage branch metadata") from exc
    if retained_branch_ids is None:
        raise ValueError(
            "Tree has no authoritative retained-branch report; regenerate it with this MTree version"
        )
    return validate_retained_branch_ids(retained_branch_ids, anchors)
