# Minion Code 工具集

本项目实现了一套完整的工具集，所有工具都继承自 minion 框架的 `BaseTool` 类，并正确设置了 `readonly` 属性。

## 工具分类

### 📁 文件系统工具

| 工具名 | 类名 | 只读 | 描述 |
|--------|------|------|------|
| `file_read` | `FileReadTool` | ✅ | 读取文件内容，支持文本文件和图片文件 |
| `file_write` | `FileWriteTool` | ❌ | 写入内容到文件 |
| `bash` | `BashTool` | ❌ | 执行 bash 命令 |
| `grep` | `GrepTool` | ✅ | 在文件中搜索文本模式 |
| `glob` | `GlobTool` | ✅ | 使用 glob 模式匹配文件 |
| `ls` | `LsTool` | ✅ | 列出目录内容 |

### 💻 执行工具

| 工具名 | 类名 | 只读 | 描述 |
|--------|------|------|------|
| `python_interpreter` | `PythonInterpreterTool` | ❌ | 执行 Python 代码 |

### 🌐 网络工具

| 工具名 | 类名 | 只读 | 描述 |
|--------|------|------|------|
| `web_search` | `WebSearchTool` | ✅ | 执行网络搜索并返回搜索结果 |
| `wikipedia_search` | `WikipediaSearchTool` | ✅ | 搜索 Wikipedia 并返回主题摘要 |
| `visit_webpage` | `VisitWebpageTool` | ✅ | 访问指定 URL 的网页并读取其内容 |

### 🤝 交互工具

| 工具名 | 类名 | 只读 | 描述 |
|--------|------|------|------|
| `user_input` | `UserInputTool` | ✅ | 向用户询问特定问题并获取输入 |
| `final_answer` | `FinalAnswerTool` | ✅ | 提供问题的最终答案 |

## Readonly 属性说明

### 只读工具 (readonly = True)
这些工具不会修改系统状态，只进行查询、读取或搜索操作：
- 文件读取工具
- 搜索工具（grep, glob）
- 目录列表工具
- 网络搜索工具
- 用户交互工具

### 读写工具 (readonly = False)
这些工具可能会修改系统状态：
- 文件写入工具
- 命令执行工具
- 代码执行工具

## 使用示例

```python
from minion_code.tools import (
    FileReadTool, WebSearchTool, FinalAnswerTool
)

# 只读工具示例
file_reader = FileReadTool()
content = file_reader.forward("example.txt")

# 网络搜索工具
search_tool = WebSearchTool()
results = search_tool.forward("Python 编程", max_results=5)

# 最终答案工具
answer_tool = FinalAnswerTool()
final_result = answer_tool.forward(
    answer="Python 是一种高级编程语言",
    confidence=0.95,
    reasoning="基于搜索结果和文档分析"
)
```

## 工具映射

所有工具都在 `TOOL_MAPPING` 字典中注册，可以通过工具名称动态获取：

```python
from minion_code.tools import TOOL_MAPPING

# 通过名称获取工具类
FileReadTool = TOOL_MAPPING['file_read']
WebSearchTool = TOOL_MAPPING['web_search']

# 创建工具实例
tool = FileReadTool()
```

## 扩展说明

### 网络工具实现注意事项
当前的网络工具（`WebSearchTool`, `WikipediaSearchTool`, `VisitWebpageTool`）是模拟实现。
实际使用时需要：

1. **WebSearchTool**: 集成真实的搜索 API（如 Google Search API, Bing API）
2. **WikipediaSearchTool**: 安装 `wikipedia-api` 包并实现真实搜索
3. **VisitWebpageTool**: 安装 `requests`, `beautifulsoup4`, `html2text` 等包

### 建议的依赖包
```bash
pip install requests beautifulsoup4 html2text wikipedia-api duckduckgo-search
```

## 测试

运行所有工具测试：
```bash
source .venv/bin/activate
PYTHONPATH=/Users/femtozheng/python-project/minion1:$PYTHONPATH python -m pytest tests/ -v
```

特定测试：
```bash
# 测试 readonly 属性
python -m pytest tests/test_readonly_tools.py -v

# 测试基本工具功能
python -m pytest tests/test_tools.py -v
```