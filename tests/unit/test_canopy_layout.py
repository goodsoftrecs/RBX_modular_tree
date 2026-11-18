"""Tests for deterministic canopy-lobe layout."""

from canopy_layout import Anchor, build_lobe_layout


def _anchors():
    return [
        Anchor(position=(-4.0, 0.0, 5.0), direction=(-1.0, 0.0, 0.1), depth=2),
        Anchor(position=(4.0, 0.0, 5.0), direction=(1.0, 0.0, 0.1), depth=2),
        Anchor(position=(0.0, -4.0, 5.5), direction=(0.0, -1.0, 0.2), depth=2),
        Anchor(position=(0.0, 4.0, 5.5), direction=(0.0, 1.0, 0.2), depth=2),
        Anchor(position=(-2.0, -2.0, 8.0), direction=(-0.2, -0.2, 1.0), depth=2),
        Anchor(position=(2.0, 2.0, 8.5), direction=(0.2, 0.2, 1.0), depth=2),
        Anchor(position=(-1.0, 1.0, 10.0), direction=(-0.1, 0.1, 1.0), depth=2),
        Anchor(position=(1.0, -1.0, 10.5), direction=(0.1, -0.1, 1.0), depth=2),
        Anchor(position=(0.0, 0.0, 11.0), direction=(0.0, 0.0, 1.0), depth=1),
    ]


def test_layout_is_deterministic_for_same_inputs():
    first = build_lobe_layout(_anchors(), count=8, scale_multiplier=1.0, seed=538)
    second = build_lobe_layout(_anchors(), count=8, scale_multiplier=1.0, seed=538)

    assert first == second


def test_layout_returns_exact_requested_count():
    layout = build_lobe_layout(_anchors(), count=6, scale_multiplier=1.0, seed=10)

    assert len(layout) == 6
    assert len({placement.anchor_index for placement in layout}) == 6


def test_layout_uses_all_template_roles():
    layout = build_lobe_layout(_anchors(), count=9, scale_multiplier=1.0, seed=20)

    assert {placement.template_name for placement in layout} == {
        "Canopy_Round",
        "Canopy_Wide",
        "Canopy_Tip",
    }


def test_scale_multiplier_scales_every_placement():
    normal = build_lobe_layout(_anchors(), count=8, scale_multiplier=1.0, seed=30)
    doubled = build_lobe_layout(_anchors(), count=8, scale_multiplier=2.0, seed=30)

    assert [placement.anchor_index for placement in normal] == [
        placement.anchor_index for placement in doubled
    ]
    for normal_placement, doubled_placement in zip(normal, doubled, strict=True):
        assert doubled_placement.scale == normal_placement.scale * 2.0


def test_sparse_anchor_fallback_remains_deterministic_and_exact():
    sparse = _anchors()[:2]

    layout = build_lobe_layout(sparse, count=5, scale_multiplier=1.0, seed=40)

    assert len(layout) == 5
    assert layout == build_lobe_layout(sparse, count=5, scale_multiplier=1.0, seed=40)


def test_invalid_inputs_fail_explicitly():
    try:
        build_lobe_layout([], count=1, scale_multiplier=1.0, seed=0)
    except ValueError as exc:
        assert "anchor" in str(exc).lower()
    else:
        raise AssertionError("Expected empty anchors to fail")

    try:
        build_lobe_layout(_anchors(), count=0, scale_multiplier=1.0, seed=0)
    except ValueError as exc:
        assert "count" in str(exc).lower()
    else:
        raise AssertionError("Expected zero count to fail")

