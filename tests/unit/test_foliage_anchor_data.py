"""Tests for versioned, Blender-independent foliage anchor persistence."""

import base64
import json
import zlib

import pytest

from foliage_anchor_data import (
    RETAINED_BRANCH_IDS_KEY,
    FoliageAnchor,
    decode_anchor_payload,
    encode_anchor_payload,
    load_retained_branch_ids,
    store_retained_branch_ids,
    validate_retained_branch_ids,
)


def _anchors():
    return [
        FoliageAnchor((1.0, 2.0, 3.0), (0.0, 0.0, 1.0), 0.25, 2, 7, 0.5),
        FoliageAnchor((-1.0, 4.0, 8.0), (1.0, 0.0, 0.0), 0.1, 3, 8, 1.0),
    ]


def test_anchor_payload_round_trip_is_stable():
    encoded = encode_anchor_payload(_anchors())

    assert decode_anchor_payload(encoded) == _anchors()
    assert encode_anchor_payload(decode_anchor_payload(encoded)) == encoded


@pytest.mark.parametrize("payload", ["", "{}", "zlib-json-v1:not-base64"])
def test_invalid_anchor_payload_fails_explicitly(payload):
    with pytest.raises(ValueError, match="payload"):
        decode_anchor_payload(payload)


def test_non_finite_anchor_values_are_rejected():
    invalid = FoliageAnchor((float("nan"), 0.0, 0.0), (0.0, 1.0, 0.0), 0.1, 1, 1, 0.5)

    with pytest.raises(ValueError, match="finite"):
        encode_anchor_payload([invalid])


def test_pre_junction_anchor_schema_requires_tree_regeneration():
    prefix, encoded_document = encode_anchor_payload(_anchors()).split(":", 1)
    document = json.loads(zlib.decompress(base64.b64decode(encoded_document)))
    document["schemaVersion"] = 1
    stale_payload = prefix + ":" + base64.b64encode(
        zlib.compress(json.dumps(document, separators=(",", ":")).encode("utf-8"))
    ).decode("ascii")

    with pytest.raises(ValueError, match="unsupported schema"):
        decode_anchor_payload(stale_payload)


def test_retained_branch_ids_round_trip_against_anchor_graph():
    wood = {}

    store_retained_branch_ids(wood, [8, 7], _anchors())

    assert wood[RETAINED_BRANCH_IDS_KEY] == [7, 8]
    assert load_retained_branch_ids(wood, _anchors()) == frozenset({7, 8})


@pytest.mark.parametrize(
    ("retained_ids", "message"),
    [
        ([], "no retained"),
        ([7, 7], "duplicates"),
        ([-1], "non-negative"),
        ([99], "absent"),
        ([7.0], "integers"),
    ],
)
def test_invalid_retained_branch_ids_fail_explicitly(retained_ids, message):
    with pytest.raises(ValueError, match=message):
        validate_retained_branch_ids(retained_ids, _anchors())


def test_missing_retained_report_requires_regeneration():
    with pytest.raises(ValueError, match="regenerate"):
        load_retained_branch_ids({}, _anchors())
