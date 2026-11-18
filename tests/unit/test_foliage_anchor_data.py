"""Tests for versioned, Blender-independent foliage anchor persistence."""

import pytest

from foliage_anchor_data import FoliageAnchor, decode_anchor_payload, encode_anchor_payload


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
