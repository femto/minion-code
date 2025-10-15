# Minion Code Tools

一个强大的Python开发工具集合，提供文件操作、代码执行、文本搜索等功能。

## 特性

- 🔧 **丰富的工具集**：文件读写、Bash执行、文本搜索、Python解释器等
- ⚡ **异步支持**：支持同步和异步两种执行模式
- 🛡️ **安全设计**：内置安全检查，防止危险操作
- 🎯 **易于扩展**：基于装饰器和类的灵活工具创建方式
- 📝 **完整文档**：详细的使用示例和API文档

## 安装

```bash
# 克隆仓库
git clone <repository-url>
cd minion-code

```

## 快速开始

### 基础工具使用

```python
from minion_code.tools import FileReadTool, FileWriteTool, BashTool

# 文件操作
write_tool = FileWriteTool()
write_tool("test.txt", "Hello, World!")

read_tool = FileReadTool()
content = read_tool("test.txt")
print(content)

# 执行命令
bash_tool = BashTool()
result = bash_tool("ls -la")
print(result)
```

### 异步工具使用

```python
import asyncio
from minion_code.tools import AsyncBaseTool, async_tool

# 使用装饰器创建异步工具
@async_tool
async def my_async_tool(data: str) -> str:
    """自定义异步工具"""
    await asyncio.sleep(1)  # 模拟异步操作
    return f"处理结果：{data}"

# 使用异步工具
async def main():
    tool = my_async_tool
    result = await tool("测试数据")
    print(result)

asyncio.run(main())
```

## 可用工具

### 文件操作工具

- **FileReadTool**: 读取文件内容，支持文本和图片文件
- **FileWriteTool**: 写入内容到文件
- **LsTool**: 列出目录内容
- **GlobTool**: 使用glob模式匹配文件

### 搜索工具

- **GrepTool**: 在文件中搜索文本模式（支持正则表达式）

### 执行工具

- **BashTool**: 执行bash命令（带安全检查）
- **PythonInterpreterTool**: 执行Python代码（受限环境）

## 工具详细说明

### FileReadTool

读取文件内容，支持偏移和限制参数。

```python
read_tool = FileReadTool()

# 读取整个文件
content = read_tool("file.txt")

# 从第10行开始读取20行
content = read_tool("file.txt", offset=10, limit=20)
```

### GrepTool

在文件中搜索文本模式。

```python
grep_tool = GrepTool()

# 在当前目录的Python文件中搜索"import"
result = grep_tool("import", ".", "*.py")
```

### BashTool

安全执行bash命令。

```python
bash_tool = BashTool()

# 执行命令
result = bash_tool("echo 'Hello World'")

# 带超时的命令执行
result = bash_tool("sleep 5", timeout=10)
```

### PythonInterpreterTool

在受限环境中执行Python代码。

```python
python_tool = PythonInterpreterTool()

code = """
import math
print(f"圆周率：{math.pi}")
"""

result = python_tool(code)
```

## 创建自定义工具

### 使用装饰器

```python
from minion_code.tools import tool

@tool
def my_custom_tool(input_text: str, multiplier: int = 2) -> str:
    """
    自定义工具示例
    
    Args:
        input_text: 输入文本
        multiplier: 重复次数
        
    Returns:
        处理后的文本
    """
    return input_text * multiplier

# 使用工具
custom_tool = my_custom_tool
result = custom_tool("Hello ", 3)  # "Hello Hello Hello "
```

### 使用类继承

```python
from minion_code.tools import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "我的自定义工具"
    inputs = {
        "data": {"type": "string", "description": "输入数据"}
    }
    output_type = "string"
    
    def forward(self, data: str) -> str:
        return f"处理结果：{data.upper()}"

# 使用工具
my_tool = MyTool()
result = my_tool("hello world")
```

## 异步工具

### 创建异步工具

```python
from minion_code.tools import AsyncBaseTool, async_tool
import asyncio

# 使用装饰器
@async_tool
async def async_process(data: str) -> str:
    """异步处理工具"""
    await asyncio.sleep(1)
    return f"异步处理：{data}"

# 使用类继承
class MyAsyncTool(AsyncBaseTool):
    name = "my_async_tool"
    description = "异步工具示例"
    inputs = {"data": {"type": "string", "description": "输入数据"}}
    output_type = "string"
    
    async def forward(self, data: str) -> str:
        await asyncio.sleep(0.5)
        return f"异步结果：{data}"
```

### 同步工具转异步

```python
from minion_code.tools import SyncToAsyncToolAdapter, FileReadTool

# 将同步工具转换为异步工具
sync_tool = FileReadTool()
async_tool = SyncToAsyncToolAdapter(sync_tool)

# 异步使用
async def main():
    result = await async_tool("file.txt")
    print(result)

asyncio.run(main())
```

## 安全特性

- **命令执行安全**：BashTool禁止执行危险命令（如`rm -rf`、`sudo`等）
- **Python执行限制**：PythonInterpreterTool在受限环境中执行，只允许安全的内置函数和指定模块
- **文件访问控制**：所有文件操作都有路径验证和错误处理

## 示例

查看 `examples/` 目录中的完整示例：

- `tool_usage_example.py`: 基础工具使用示例
- `async_tool_example.py`: 异步工具使用示例

运行示例：

```bash
python examples/tool_usage_example.py
python examples/async_tool_example.py
```

## 贡献

欢迎提交Issue和Pull Request来改进这个项目！

## 许可证

MIT License