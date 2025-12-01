# FileReadTool Enhancements

## Overview

The `FileReadTool` has been enhanced to support image reading and the `format_for_observation` pattern documented in [TOOL_OBSERVATION_FORMATTING.md](TOOL_OBSERVATION_FORMATTING.md).

## Key Features

### 1. Image Support

The tool can now read image files and return PIL.Image objects:

```python
tool = FileReadTool()

# Read an image file
result = tool.forward("path/to/image.png")
# Returns: PIL.Image object
```

Supported image formats:
- PNG, JPG/JPEG, GIF, BMP, WEBP, TIFF, SVG

### 2. Format for Observation

The `format_for_observation()` method provides different formatting based on content type:

#### For Text Files

When reading text files, `forward()` returns plain text, but `format_for_observation()` adds:
- Line numbers (using `→` separator)
- File metadata (path, total lines, displayed range)
- Proper formatting for LLM consumption

Example:
```python
tool = FileReadTool()
content = tool.forward("example.py")
# Returns: "def hello():\n    print('hi')\n"

formatted = tool.format_for_observation(content)
# Returns:
# File: example.py
# Total lines: 2
#
#     1→def hello():
#     2→    print('hi')
```

#### For Images

When reading images, `forward()` returns a PIL.Image object, but `format_for_observation()` converts it to base64 encoding suitable for LLM consumption:

```python
tool = FileReadTool()
image = tool.forward("photo.png")
# Returns: <PIL.Image.Image object>

formatted = tool.format_for_observation(image)
# Returns:
# Image file: photo.png
# Size: 800x600 pixels
# Mode: RGB
# Format: PNG
#
# Base64 encoded image:
# data:image/png;base64,iVBORw0KG...
```

### 3. State Tracking

The tool maintains state about the last execution to properly format output with correct line numbers:

```python
tool = FileReadTool()

# Read lines 5-10 (offset=4, limit=6)
content = tool.forward("file.txt", offset=4, limit=6)

# format_for_observation knows to start numbering at line 5
formatted = tool.format_for_observation(content)
# Line numbers will be: 5, 6, 7, 8, 9, 10
```

State tracked:
- `_last_file_path`: Path of the last read file
- `_last_offset`: Offset parameter used
- `_last_limit`: Limit parameter used
- `_last_total_lines`: Total lines in the file (for text files)

## Implementation Details

### Return Types

The `forward()` method now has a flexible return type:
- **Text files**: Returns `str` with raw content
- **Image files**: Returns `PIL.Image` object
- **Errors**: Returns `str` with error message

### Dependencies

Pillow (PIL) is now a required dependency:
```toml
dependencies = [
    "minionx",
    "typer>=0.9.0",
    "Pillow>=10.0.0"
]
```

If PIL is not available, image reading will return an error message instead of crashing.

## Usage Examples

### Basic Text Reading
```python
tool = FileReadTool()
content = tool.forward("config.json")
formatted = tool.format_for_observation(content)
# Formatted output includes line numbers for easy reference
```

### Reading Specific Lines
```python
tool = FileReadTool()
# Read lines 10-20
content = tool.forward("large_file.py", offset=9, limit=11)
formatted = tool.format_for_observation(content)
# Line numbers start at 10
```

### Reading Images
```python
tool = FileReadTool()
image = tool.forward("diagram.png")

# For code usage
width, height = image.size
pixels = image.load()

# For LLM observation
formatted = tool.format_for_observation(image)
# Returns base64 encoded image
```

## Benefits

1. **Single tool for multiple purposes**: One tool handles both programmatic access and LLM observation
2. **Better LLM understanding**: Line numbers make it easier for LLMs to reference specific lines
3. **Image support**: LLMs can now "see" images through base64 encoding
4. **Maintains state**: Correct line numbering even with offset/limit parameters
5. **Backward compatible**: Error messages and simple strings still work as expected

## Testing

Run the standalone demo to see all features in action:
```bash
python3 test_standalone.py
```

Or run the full test suite:
```bash
pytest tests/test_file_read_tool.py -v
```

## Future Enhancements

Potential future improvements:
- Syntax highlighting in formatted output
- Smart truncation for very large files
- Support for binary file inspection
- Image thumbnail generation
- PDF text extraction
