#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for FileReadTool with image support and format_for_observation
"""

import os
import tempfile
from pathlib import Path
import pytest

# Import the tool
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from minion_code.tools.file_read_tool import FileReadTool

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class TestFileReadTool:
    """Test FileReadTool functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        self.tool = FileReadTool()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Cleanup test fixtures"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_read_text_file(self):
        """Test reading a text file"""
        # Create test file
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Line 1\nLine 2\nLine 3\n")

        # Read file
        result = self.tool.forward(test_file)
        assert isinstance(result, str)
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_format_for_observation_text(self):
        """Test format_for_observation with text content"""
        # Create test file
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Line 1\nLine 2\nLine 3\n")

        # Read file
        result = self.tool.forward(test_file)

        # Format for observation
        formatted = self.tool.format_for_observation(result)

        # Check that line numbers are present
        assert "1→" in formatted or "    1→" in formatted
        assert "2→" in formatted or "    2→" in formatted
        assert "3→" in formatted or "    3→" in formatted
        assert test_file in formatted
        assert "Total lines:" in formatted

    def test_format_for_observation_with_offset(self):
        """Test format_for_observation with offset parameter"""
        # Create test file
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")

        # Read file with offset
        result = self.tool.forward(test_file, offset=2, limit=2)

        # Format for observation
        formatted = self.tool.format_for_observation(result)

        # Check that line numbers start from offset
        assert "3→" in formatted or "    3→" in formatted
        assert "4→" in formatted or "    4→" in formatted
        # Should not contain line 1 and 2
        assert "Line 1" not in result
        assert "Line 2" not in result

    @pytest.mark.skipif(not HAS_PIL, reason="PIL not available")
    def test_read_image_file(self):
        """Test reading an image file"""
        # Create a simple test image
        test_image = os.path.join(self.temp_dir, "test.png")
        img = Image.new('RGB', (100, 100), color='red')
        img.save(test_image)

        # Read image
        result = self.tool.forward(test_image)

        # Should return PIL Image object
        assert isinstance(result, Image.Image)
        assert result.size == (100, 100)

    @pytest.mark.skipif(not HAS_PIL, reason="PIL not available")
    def test_format_for_observation_image(self):
        """Test format_for_observation with image"""
        # Create a simple test image
        test_image = os.path.join(self.temp_dir, "test.png")
        img = Image.new('RGB', (100, 100), color='blue')
        img.save(test_image)

        # Read image
        result = self.tool.forward(test_image)

        # Format for observation
        formatted = self.tool.format_for_observation(result)

        # Check that it contains base64 encoding
        assert "base64" in formatted.lower()
        assert "100x100" in formatted
        assert test_image in formatted
        assert "Image file:" in formatted

    def test_nonexistent_file(self):
        """Test reading a nonexistent file"""
        result = self.tool.forward("/nonexistent/file.txt")
        assert "Error" in result
        assert "does not exist" in result

    def test_error_format_for_observation(self):
        """Test that errors are passed through format_for_observation"""
        result = self.tool.forward("/nonexistent/file.txt")
        formatted = self.tool.format_for_observation(result)
        assert "Error" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
