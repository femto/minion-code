"""Basic tests for the minion-code package."""

import sys
import os
import pytest

# 添加 minion 框架路径
sys.path.insert(0, "/Users/femtozheng/python-project/minion1")

from minion_code import __init__


def test_package_imports():
    """Test that the package can be imported."""
    assert __init__ is not None


def test_basic_functionality():
    """Basic test to ensure CI pipeline works."""
    assert 1 + 1 == 2
