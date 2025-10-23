# MinionCodeAgent

一个增强的AI代码助手，基于Minion框架构建，预配置了丰富的开发工具，专为代码开发任务优化。

## 特性

- 🤖 **智能代码助手**：预配置的AI agent，专为编程任务设计
- 🔧 **丰富的工具集**：自动包含文件操作、命令执行、网络搜索等12+个工具
- ⚡ **即开即用**：一行代码创建，无需复杂配置
- 📝 **对话历史**：内置对话历史跟踪和管理
- 🎯 **优化提示**：专为代码开发任务优化的系统提示
- 🛡️ **安全设计**：内置安全检查，防止危险操作

## 安装

```bash
# 克隆仓库
git clone <repository-url>
cd minion-code
pip install -e .
```

## 快速开始

### CLI使用

```bash
# 基本使用
mcode

# 指定工作目录
mcode --dir /path/to/project

# 启用详细输出
mcode --verbose

# 使用MCP配置文件加载额外工具
mcode --config mcp.json

# 组合使用
mcode --dir /path/to/project --config mcp.json --verbose
```

### 编程接口

```python
import asyncio
from minion_code import MinionCodeAgent

async def main():
    # 创建AI代码助手，自动配置所有工具
    agent = await MinionCodeAgent.create(
        name="My Code Assistant",
        llm="gpt-4.1"
    )
    
    # 与AI助手对话
    response = await agent.run_async("List files in current directory")
    print(response.answer)
    
    response = await agent.run_async("Read the README.md file")
    print(response.answer)

asyncio.run(main())
```

### 自定义配置

```python
# 自定义系统提示和工作目录
agent = await MinionCodeAgent.create(
    name="Python Expert",
    llm="gpt-4.1",
    system_prompt="You are a specialized Python developer assistant.",
    workdir="/path/to/project",
    additional_tools=[MyCustomTool()]
)
```

### 查看可用工具

```python
# 打印工具摘要
agent.print_tools_summary()

# 获取工具信息
tools_info = agent.get_tools_info()
for tool in tools_info:
    print(f"{tool['name']}: {tool['description']}")
```

## 内置工具

MinionCodeAgent自动包含以下工具类别：

### 📁 文件和目录工具
- **FileReadTool**: 读取文件内容
- **FileWriteTool**: 写入文件
- **GrepTool**: 在文件中搜索文本
- **GlobTool**: 文件模式匹配
- **LsTool**: 列出目录内容

### 💻 系统和执行工具
- **BashTool**: 执行shell命令
- **PythonInterpreterTool**: 执行Python代码

### 🌐 网络和搜索工具
- **WebSearchTool**: 网络搜索
- **WikipediaSearchTool**: Wikipedia搜索
- **VisitWebpageTool**: 访问网页

### 🔧 其他工具
- **UserInputTool**: 用户输入
- **TodoWriteTool**: 任务管理写入
- **TodoReadTool**: 任务管理读取

## MCP工具集成

MinionCodeAgent支持通过MCP (Model Context Protocol) 配置文件加载额外的工具。

### MCP配置文件格式

创建一个JSON配置文件（如`mcp.json`）：

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    },
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem", "/tmp"],
      "disabled": true,
      "autoApprove": ["read_file", "list_directory"]
    },
    "git": {
      "command": "uvx", 
      "args": ["mcp-server-git"],
      "disabled": false,
      "autoApprove": ["git_status", "git_log"]
    }
  }
}
```

### 配置选项说明

- `command`: 启动MCP服务器的命令
- `args`: 命令参数列表
- `env`: 环境变量（可选）
- `disabled`: 是否禁用此服务器（默认false）
- `autoApprove`: 自动批准的工具名称列表（可选）

### 使用MCP配置

```bash
# 使用MCP配置文件
minion-code --config examples/mcp_config.json

# 查看加载的工具（包括MCP工具）
# 在CLI中输入: tools
```

### 编程接口中使用MCP工具

```python
from minion_code.utils.mcp_loader import load_mcp_tools
from pathlib import Path

async def main():
    # 加载MCP工具
    mcp_tools = await load_mcp_tools(Path("mcp.json"))
    
    # 创建包含MCP工具的agent
    agent = await MinionCodeAgent.create(
        name="Enhanced Assistant",
        llm="gpt-4o-mini",
        additional_tools=mcp_tools
    )
```

## 对话历史管理

```python
# 获取对话历史
history = agent.get_conversation_history()
for entry in history:
    print(f"User: {entry['user_message']}")
    print(f"Agent: {entry['agent_response']}")

# 清除历史
agent.clear_conversation_history()
```

## 与原始实现的对比

### 之前 (复杂的手动配置)
```python
# 需要手动导入和配置所有工具
from minion_code.tools import (
    FileReadTool, FileWriteTool, BashTool, 
    GrepTool, GlobTool, LsTool, 
    PythonInterpreterTool, WebSearchTool,
    # ... 更多工具
)

# 手动创建工具实例
custom_tools = [
    FileReadTool(),
    FileWriteTool(),
    BashTool(),
    # ... 更多工具配置
]

# 手动设置系统提示
SYSTEM_PROMPT = "You are a coding agent..."

# 创建agent (约50行代码)
agent = await CodeAgent.create(
    name="Minion Code Assistant",
    llm="gpt-4o-mini",
    system_prompt=SYSTEM_PROMPT,
    tools=custom_tools,
)
```

### 现在 (使用MinionCodeAgent)
```python
# 一行代码完成所有设置
agent = await MinionCodeAgent.create(
    name="Minion Code Assistant",
    llm="gpt-4o-mini"
)
```

## API参考

### MinionCodeAgent.create()

```python
async def create(
    name: str = "Minion Code Assistant",
    llm: str = "gpt-4o-mini", 
    system_prompt: Optional[str] = None,
    workdir: Optional[Union[str, Path]] = None,
    additional_tools: Optional[List[Any]] = None,
    **kwargs
) -> MinionCodeAgent
```

**参数:**
- `name`: Agent名称
- `llm`: 使用的LLM模型
- `system_prompt`: 自定义系统提示（可选）
- `workdir`: 工作目录（可选，默认当前目录）
- `additional_tools`: 额外工具列表（可选）
- `**kwargs`: 传递给CodeAgent.create()的其他参数

### 实例方法

- `run_async(message: str)`: 异步运行agent
- `run(message: str)`: 同步运行agent  
- `get_conversation_history()`: 获取对话历史
- `clear_conversation_history()`: 清除对话历史
- `get_tools_info()`: 获取工具信息
- `print_tools_summary()`: 打印工具摘要

### 属性

- `agent`: 访问底层CodeAgent实例
- `tools`: 获取可用工具列表
- `name`: 获取agent名称

## 安全特性

- **命令执行安全**：BashTool禁止执行危险命令（如`rm -rf`、`sudo`等）
- **Python执行限制**：PythonInterpreterTool在受限环境中执行，只允许安全的内置函数和指定模块
- **文件访问控制**：所有文件操作都有路径验证和错误处理

## 示例

查看 `examples/` 目录中的完整示例：

- `simple_code_agent.py`: 基本MinionCodeAgent使用示例
- `simple_tui.py`: 简化的TUI实现
- `advanced_textual_tui.py`: 高级TUI界面（使用Textual库）
- `minion_agent_tui.py`: 原始复杂实现（对比参考）
- `mcp_config.json`: MCP配置文件示例
- `test_mcp_config.py`: MCP配置加载测试
- `demo_mcp_cli.py`: MCP CLI功能演示

运行示例：

```bash
# 基本使用示例
python examples/simple_code_agent.py

# 简单TUI
python examples/simple_tui.py

# 高级TUI (需要安装 textual: pip install textual rich)
python examples/advanced_textual_tui.py

# 测试MCP配置加载
python examples/test_mcp_config.py

# MCP CLI功能演示
python examples/demo_mcp_cli.py
```

## 文档

- [MCP工具集成指南](docs/MCP_GUIDE.md) - 详细的MCP配置和使用指南

## 贡献

欢迎提交Issue和Pull Request来改进这个项目！

## 许可证

MIT License