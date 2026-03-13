from __future__ import annotations

from pathlib import Path

from minion_code.utils.runtime_paths import ensure_minion_root_env


def test_ensure_minion_root_env_creates_logs_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("MINION_ROOT", raising=False)

    root = ensure_minion_root_env(tmp_path / "minion-runtime")

    assert root == tmp_path / "minion-runtime"
    assert Path(root).exists()
    assert (Path(root) / "logs").exists()
