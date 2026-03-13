#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Backward-compatible shim for older runtime_paths imports."""

from ..runtime_paths import DEFAULT_MINION_ROOT, ensure_minion_root_env

__all__ = ["DEFAULT_MINION_ROOT", "ensure_minion_root_env"]
