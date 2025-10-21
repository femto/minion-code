# MCP工具集成指南

本指南详细介绍如何在MinionCodeAgent中使用MCP (Model Context Protocol) 工具。

## 什么是MCP？

MCP (Model Context Protocol) 是一个标准协议，允许AI应用程序与外部工具和服务进行交互。通过MCP，你可以轻松地为AI助手添加各种功能，如文件系统访问、网络请求、数据库操作等。

## 快速开始

### 1. 创建MCP配置文件

创建一个JSON配置文件（例如 `mcp.json`）：

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
    }
  }
}
```

### 2. 使用CLI启动

```bash
# 使用MCP配置启动CLI
minion-code --config mcp.json

# 组合使用多个选项
minion-code --config mcp.json --dir /path/to/project --verbose
```

### 3. 在代码中使用

```python
from minion_code.utils.mcp_loader import load_mcp_tools
from minion_code import MinionCodeAgent
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
    
    # 使用agent
    response = await agent.run_async("List available tools")
    print(response.answer)
```

## 配置选项详解

### 服务器配置

每个MCP服务器配置包含以下字段：

- **command** (必需): 启动MCP服务器的命令
- **args** (必需): 命令参数列表
- **env** (可选): 环境变量字典
- **disabled** (可选): 是否禁用此服务器，默认为 `false`
- **autoApprove** (可选): 自动批准的工具名称列表

### 示例配置

```json
{
  "mcpServers": {
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git"],
      "disabled": false,
      "autoApprove": ["git_status", "git_log"]
    },
    "web": {
      "command": "npx",
      "args": ["-y", "web-mcp-server@latest"],
      "env": {
        "API_KEY": "your-api-key",
        "DEBUG": "true"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## 常用MCP服务器

### 文件系统服务器

```json
{
  "filesystem": {
    "command": "uvx",
    "args": ["mcp-server-filesystem", "/path/to/workspace"],
    "autoApprove": ["read_file", "list_directory"]
  }
}
```

### Git服务器

```json
{
  "git": {
    "command": "uvx",
    "args": ["mcp-server-git"],
    "autoApprove": ["git_status", "git_log", "git_diff"]
  }
}
```

### Chrome DevTools服务器

```json
{
  "chrome-devtools": {
    "command": "npx",
    "args": ["-y", "chrome-devtools-mcp@latest"],
    "env": {
      "FASTMCP_LOG_LEVEL": "ERROR"
    }
  }
}
```

## 高级用法

### 编程接口

```python
from minion_code.utils.mcp_loader import MCPToolsLoader

async def advanced_usage():
    # 创建加载器
    loader = MCPToolsLoader(Path("mcp.json"))
    
    # 加载配置
    servers = loader.load_config()
    print(f"Found {len(servers)} servers")
    
    # 加载工具
    tools = await loader.load_all_tools()
    print(f"Loaded {len(tools)} tools")
    
    # 获取服务器信息
    info = loader.get_server_info()
    for name, details in info.items():
        print(f"{name}: {details['command']} ({'enabled' if not details['disabled'] else 'disabled'})")
    
    # 清理资源
    await loader.close()
```

### 动态配置

```python
from minion_code.utils.mcp_loader import MCPServerConfig, MCPToolsLoader

async def dynamic_config():
    # 创建动态配置
    loader = MCPToolsLoader()
    
    # 手动添加服务器配置
    loader.servers["custom"] = MCPServerConfig(
        name="custom",
        command="python",
        args=["my_mcp_server.py"],
        env={"CUSTOM_VAR": "value"}
    )
    
    # 加载工具
    tools = await loader.load_all_tools()
    
    # 清理
    await loader.close()
```

## 故障排除

### 常见问题

1. **MCP服务器无法启动**
   - 检查命令和参数是否正确
   - 确保所需的依赖已安装
   - 查看详细日志：使用 `--verbose` 选项

2. **工具加载失败**
   - 检查服务器是否正确响应MCP协议
   - 验证环境变量设置
   - 查看服务器日志

3. **权限问题**
   - 确保有执行MCP服务器命令的权限
   - 检查文件系统访问权限

### 调试技巧

```bash
# 启用详细日志
minion-code --config mcp.json --verbose

# 测试配置文件
python examples/test_mcp_config.py
```

```python
# 在代码中启用调试
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 最佳实践

1. **安全性**
   - 仅启用必需的MCP服务器
   - 使用 `autoApprove` 谨慎地自动批准安全的操作
   - 定期审查配置文件

2. **性能**
   - 禁用不需要的服务器（设置 `disabled: true`）
   - 合理设置环境变量
   - 及时清理资源

3. **维护性**
   - 使用描述性的服务器名称
   - 添加注释说明配置用途
   - 版本控制配置文件

## 扩展开发

如果你想开发自己的MCP服务器，请参考：

- [MCP官方文档](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [示例MCP服务器](https://github.com/modelcontextprotocol/servers)

## 支持

如果遇到问题，请：

1. 查看本指南的故障排除部分
2. 运行测试脚本验证配置
3. 提交Issue到项目仓库