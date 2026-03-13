#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Runtime path helpers that avoid import-time writes from heavy packages."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


DEFAULT_MINION_ROOT = Path.home() / ".minion" / "runtime"


def ensure_minion_root_env(preferred_root: Optional[Path | str] = None) -> Path:
    """Ensure MINION_ROOT points to a writable runtime directory."""
    existing = os.environ.get("MINION_ROOT")
    if existing:
        root = Path(existing).expanduser()
    elif preferred_root is not None:
        root = Path(preferred_root).expanduser()
    else:
        root = DEFAULT_MINION_ROOT

    root.mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)
    os.environ["MINION_ROOT"] = str(root)
    return root
