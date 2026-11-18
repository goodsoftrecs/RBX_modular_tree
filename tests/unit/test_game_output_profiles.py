"""Tests for game-output wood mesher profiles."""

from game_output_profiles import (
    AUTHORING,
    ROBLOX_GAME,
    ROBLOX_GAME_BUDGET,
    ROBLOX_GAME_BUDGET_SETTINGS,
    ROBLOX_GAME_SETTINGS,
    resolve_wood_mesher_settings,
)


def test_authoring_profile_preserves_user_settings():
    settings = resolve_wood_mesher_settings(AUTHORING, 24, 3)

    assert settings.radial_resolution == 24
    assert settings.smooth_iterations == 3
    assert settings.longitudinal_stride == 1
    assert settings.max_branch_depth == -1
    assert settings.minimum_branch_radius_ratio == 0.0


def test_authoring_profile_clamps_invalid_settings():
    settings = resolve_wood_mesher_settings(AUTHORING, 1, -2)

    assert settings.radial_resolution == 3
    assert settings.smooth_iterations == 0
    assert settings.longitudinal_stride == 1
    assert settings.max_branch_depth == -1
    assert settings.minimum_branch_radius_ratio == 0.0


def test_roblox_game_profile_uses_low_detail_wood_settings():
    settings = resolve_wood_mesher_settings(ROBLOX_GAME, 32, 4)

    assert settings == ROBLOX_GAME_SETTINGS
    assert settings.radial_resolution == 8
    assert settings.smooth_iterations == 1
    assert settings.longitudinal_stride == 4
    assert settings.max_branch_depth == -1
    assert settings.minimum_branch_radius_ratio == 0.0


def test_roblox_budget_profile_prunes_small_deep_branch_families():
    settings = resolve_wood_mesher_settings(ROBLOX_GAME_BUDGET, 32, 4)

    assert settings == ROBLOX_GAME_BUDGET_SETTINGS
    assert settings.radial_resolution == 8
    assert settings.longitudinal_stride == 6
    assert settings.max_branch_depth == 3
    assert settings.minimum_branch_radius_ratio == 0.0
