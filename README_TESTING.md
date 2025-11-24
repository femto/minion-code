# Testing FileReadTool Enhancements

## Quick Test (Recommended)

The easiest way to test the new features is to use the standalone test:

```bash
python test_standalone.py
```

This file is completely self-contained and doesn't require any package imports from minion-code.

## If You Get Circular Import Errors

If you're experiencing circular import errors like:

```
ImportError: cannot import name 'BaseTool' from partially initialized module 'minion.tools.base_tool'
```

This is due to a circular dependency in the minion package itself. Use one of these workarounds:

### Option 1: Use test_standalone.py (Best)

```bash
python test_standalone.py
```

This file has a complete standalone implementation and won't trigger circular imports.

### Option 2: Install Pillow for Image Support

To test image features, install Pillow first:

```bash
pip install Pillow
```

Then run:

```bash
python test_standalone.py
```

### Option 3: Test via pytest (if available)

If pytest is installed and the circular import is fixed:

```bash
pytest tests/test_file_read_tool.py -v
```

## What to Look For

When running the tests, you should see:

1. **Text File Demo**: Shows raw output vs formatted output with line numbers
2. **Text with Offset**: Shows correct line numbering when using offset parameter
3. **Image File Demo**: Shows base64 encoding (if PIL is installed)

Example output:

```
👁️  Formatted for observation (with line numbers):
------------------------------------------------------------
File: /tmp/example.py
Total lines: 8

    1→def hello_world():
    2→    print('Hello, World!')
    3→
    4→def add(a, b):
    5→    return a + b
```

## Integration Testing

To test the FileReadTool in your actual minion-code environment:

1. First, ensure the circular import in minion is resolved
2. Then you can import normally:

```python
from minion_code.tools.file_read_tool import FileReadTool

tool = FileReadTool()
result = tool.forward("myfile.txt")
formatted = tool.format_for_observation(result)
print(formatted)
```

## Features Tested

- ✓ Text file reading with plain output
- ✓ Line number formatting in `format_for_observation()`
- ✓ Offset and limit parameters with correct line numbering
- ✓ Image file reading (returns PIL.Image)
- ✓ Base64 encoding for images in `format_for_observation()`
- ✓ State tracking across invocations
- ✓ Error handling
