"""Permanent redirects for migrated public URLs."""

from __future__ import annotations

from game_catalog import build_redirect_map


REDIRECTS_301: dict[str, str] = build_redirect_map()

