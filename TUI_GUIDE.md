# Minion CodeAgent TUI 指南

本项目提供了多种 TUI（文本用户界面）来与 Minion CodeAgent 交互，集成了完整的 minion_code 工具集。

## 🚀 可用的 TUI

### 1. 简单控制台 TUI
**文件**: `examples/minion_agent_tui.py`  
**命令**: `minion-agent`

基于命令行的简单交互界面，使用 Minion CodeAgent。

**特性**:
- 与 AI 代理的自然语言对话
- 自动工具选择和执行
- 会话历史记录
- 所有 minion_code 工具集成
- 原始函数自动转换为工具

**使用方法**:
```bash
# 设置环境
source .venv/bin/activate
source setup_env.sh

# 运行 TUI
minion-agent
# 或者
python examples/minion_agent_tui.py
```

### 2. 高级 Textual TUI
**文件**: `examples/advanced_textual_tui.py`  
**命令**: `minion-tui`

使用 Textual 库的富文本界面，提供更好的用户体验。

**特性**:
- 富文本界面，支持面板、标签页
- 实时聊天界面
- 工具状态可视化
- 会话历史管理
- 键盘快捷键支持
- Markdown 渲染

**依赖安装**:
```bash
pip install -e ".[tui]"
```

**使用方法**:
```bash
# 设置环境
source .venv/bin/activate
source setup_env.sh

# 运行高级 TUI
minion-tui
# 或者
python examples/advanced_textual_tui.py
```

**键盘快捷键**:
- `Ctrl+C`: 退出应用
- `Ctrl+H`: 切换到帮助标签页
- `Ctrl+T`: 显示工具信息
- `Ctrl+R`: 清除聊天记录
- `Enter`: 发送消息

### 3. 传统工具控制台
**文件**: `examples/console_demo.py` / `examples/textual_demo.py`  
**命令**: `mc` / `mcode`

传统的工具控制台，直接调用工具而不使用 AI 代理。

## 🛠️ 集成的工具

所有 TUI 都集成了以下工具：

### 📁 文件系统工具
- `FileReadTool`: 读取文件内容
- `FileWriteTool`: 写入文件内容
- `GrepTool`: 文本搜索
- `GlobTool`: 文件模式匹配
- `LsTool`: 目录列表
- `BashTool`: 执行 bash 命令

### 💻 执行工具
- `PythonInterpreterTool`: 执行 Python 代码

### 🌐 网络工具
- `WebSearchTool`: 网络搜索
- `WikipediaSearchTool`: Wikipedia 搜索
- `VisitWebpageTool`: 网页访问

### 🤝 交互工具
- `UserInputTool`: 用户输入
- `FinalAnswerTool`: 最终答案

## 💬 使用示例

### 文件操作
```
👤 You: Read the contents of README.md
🤖 Agent: I'll read the README.md file for you...
[使用 FileReadTool 读取文件]

👤 You: Write "Hello World" to test.txt
🤖 Agent: I'll create a test.txt file with "Hello World"...
[使用 FileWriteTool 写入文件]
```

### 系统操作
```
👤 You: List all Python files in the current directory
🤖 Agent: I'll search for Python files...
[使用 GlobTool 查找 *.py 文件]

👤 You: Execute the command "ls -la"
🤖 Agent: I'll run that command for you...
[使用 BashTool 执行命令]
```

### 代码执行
```
👤 You: Run Python code to calculate 15 + 27 * 3
🤖 Agent: I'll execute Python code to calculate that...
[使用 PythonInterpreterTool 执行代码]

👤 You: Run Python code to print the current date
🤖 Agent: I'll execute Python code to get the current date...
[使用 PythonInterpreterTool 执行代码]
```

### 网络操作
```
👤 You: Search for Python tutorials
🤖 Agent: I'll search the web for Python tutorials...
[使用 WebSearchTool 进行搜索]

👤 You: Look up "machine learning" on Wikipedia
🤖 Agent: I'll search Wikipedia for machine learning...
[使用 WikipediaSearchTool 搜索]
```

## 🔧 环境设置

### 必需设置
```bash
# 1. 激活虚拟环境
source .venv/bin/activate

# 2. 设置 PYTHONPATH（重要！）
source setup_env.sh
# 或手动设置
export PYTHONPATH="/Users/femtozheng/python-project/minion1:$PYTHONPATH"

# 3. 安装依赖
pip install -e ".[tui,agent]"
```

### 可选依赖
```bash
# TUI 界面依赖
pip install textual rich

# AI 代理依赖
pip install openai

# 网络工具依赖（用于真实实现）
pip install requests beautifulsoup4 html2text wikipedia-api duckduckgo-search
```

## 🧪 测试

运行集成测试：
```bash
python examples/test_agent_integration.py
```

运行所有测试：
```bash
python -m pytest tests/ -v
```

## 🔍 故障排除

### 常见问题

1. **ModuleNotFoundError: No module named 'minion'**
   ```bash
   # 确保设置了正确的 PYTHONPATH
   source setup_env.sh
   ```

2. **Agent setup failed**
   ```bash
   # 检查 OpenAI API 密钥
   export OPENAI_API_KEY="your-api-key"
   ```

3. **Tool import errors**
   ```bash
   # 重新安装项目
   pip install -e .
   ```

### 调试模式
```bash
# 启用详细日志
export MINION_LOG_LEVEL=DEBUG
python examples/minion_agent_tui.py
```

## 📚 扩展指南

### 添加新工具
1. 在 `minion_code/tools/` 中创建新工具文件
2. 继承 `BaseTool` 类
3. 在 `__init__.py` 中导入和注册
4. 重新安装项目：`pip install -e .`

### 自定义 TUI
1. 复制现有 TUI 文件
2. 修改工具集合和界面布局
3. 添加到 `pyproject.toml` 的脚本部分

### 集成外部工具
```python
# 在 TUI 中添加原始函数
def my_custom_tool(param: str) -> str:
    """My custom tool description."""
    return f"Processed: {param}"

# 添加到工具列表
raw_functions = [my_custom_tool]
all_tools = custom_tools + raw_functions
```

## 🎯 最佳实践

1. **明确的指令**: 使用具体、明确的自然语言指令
2. **工具组合**: 让 AI 代理选择最佳的工具组合
3. **错误处理**: 检查工具执行结果和错误信息
4. **会话管理**: 利用会话历史进行上下文相关的对话
5. **性能优化**: 对于频繁操作，考虑使用批处理命令