"""Basic tests for the minion-code package."""

import pytest
from minion_code import __init__


def test_package_imports():
    """Test that the package can be imported."""
    assert __init__ is not None


def test_basic_functionality():
    """Basic test to ensure CI pipeline works."""
    assert 1 + 1 == 2