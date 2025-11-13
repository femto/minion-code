# LLM 配置指南

本文档说明如何为 minion-code 配置大语言模型（LLM）。

## 项目依赖说明

minion-code 依赖于 [Minion](https://github.com/femto/minion) 框架。根据不同的安装方式，`MINION_ROOT` 的位置也会不同。

### 安装方式一：从源码安装（推荐开发使用）

如果你想从源码安装并开发调试：

```bash
# 克隆 minion 仓库
git clone https://github.com/femto/minion

# 克隆 minion-code 仓库
git clone https://github.com/femto/minion-code

# 进入 minion-code 目录
cd minion-code

# 以开发模式安装 minion 依赖（从本地路径）
pip install -e ../minion

# 安装 minion-code
pip install -e .
```

在这种情况下，`MINION_ROOT` 将位于 `../minion` 目录。

### 安装方式二：直接安装（推荐一般使用）

如果你只需要使用而不需要修改 minion 框架：

```bash
# 克隆 minion-code 仓库
git clone https://github.com/femto/minion-code
cd minion-code

# 安装 minionx（会自动安装依赖）
pip install minionx

# 安装 minion-code
pip install -e .
```

在这种情况下，`MINION_ROOT` 将位于当前启动程序的位置（通常是当前工作目录）。

### 确认 MINION_ROOT 位置

启动程序时，会在日志中显示 `MINION_ROOT` 的路径：

```
2025-11-13 12:21:48.042 | INFO     | minion.const:get_minion_root:44 - MINION_ROOT set to: <some_path>
```

例如：
```
2025-11-13 12:21:48.042 | INFO     | minion.const:get_minion_root:44 - MINION_ROOT set to: /home/user/projects/minion
```

## LLM 配置

### 支持的 LLM 提供商

minion-code 支持多种 LLM 提供商：

- **Anthropic**: Claude 系列模型（sonnet, haiku, opus 等）
- **OpenAI**: GPT 系列模型（gpt-4o, gpt-4o-mini, o1-mini, gpt-5 等）
- **其他**: Mistral, DeepSeek, Kimi, Qwen, GLM, MiniMax, Baidu Qianfan, SiliconFlow, BigDream, OpenDev, xAI, Groq, Gemini, Ollama, Azure 等

### 配置 API Keys

通过环境变量配置 API 密钥：

#### Anthropic (Claude)

```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

#### OpenAI (GPT)

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

#### 其他提供商

其他提供商的 API 密钥配置请参考各自的文档。通常需要在创建 agent 时通过配置文件或参数指定。

### 在代码中配置 LLM

#### 基本使用

```python
import asyncio
from minion_code.agents import MinionCodeAgent

async def main():
    # 使用默认模型（sonnet）
    agent = await MinionCodeAgent.create(
        name="My Code Assistant",
        llm="sonnet"
    )

    response = await agent.run_async("列出当前目录的文件")
    print(response.answer)

asyncio.run(main())
```

#### 指定特定模型

```python
# 使用 OpenAI GPT-4o
agent = await MinionCodeAgent.create(
    name="GPT Assistant",
    llm="gpt-4o"
)

# 使用 Claude Haiku (更快，更便宜)
agent = await MinionCodeAgent.create(
    name="Fast Assistant",
    llm="haiku"
)

# 使用 Claude Opus (最强大)
agent = await MinionCodeAgent.create(
    name="Powerful Assistant",
    llm="opus"
)
```

#### 为不同任务配置不同的模型

minion-code 支持为不同类型的任务使用不同的模型，以优化性能和成本：

```python
agent = await MinionCodeAgent.create(
    name="Multi-Model Assistant",
    llm="sonnet",  # 主对话模型
    llms={
        'quick': 'haiku',      # 快速任务（简单查询、格式化等）
        'task': 'sonnet',      # 任务工具（需要推理的复杂任务）
        'reasoning': 'o1-mini' # 推理任务（需要深度思考）
    }
)
```

**任务类型说明：**

- **main**: 主对话模型，用于一般的对话交互
- **quick**: 快速任务模型，用于简单、快速的查询（如格式化、简单转换）
- **task**: 任务工具模型，用于需要工具调用的复杂任务
- **reasoning**: 推理模型，用于需要深度推理的复杂问题

#### 动态更新 LLM 配置

```python
# 创建 agent
agent = await MinionCodeAgent.create(name="Assistant", llm="sonnet")

# 稍后更新配置
agent.update_llm_config(
    quick='haiku',
    reasoning='o1-mini'
)

# 查看当前配置
config = agent.get_llm_config()
print(config)
# 输出: {'main': <Provider>, 'quick': 'haiku', 'task': 'sonnet', 'reasoning': 'o1-mini'}
```

#### 使用快速查询（绕过 agent 工具）

对于不需要工具调用的简单查询，可以使用 `query_quick` 方法：

```python
# 快速查询，不使用工具
response = await agent.query_quick(
    user_prompt="什么是 Python？",
    system_prompt="你是一个编程语言专家。"
)
print(response)
```

### 在 CLI 中使用

#### 基本使用

```bash
# 使用默认模型
mcode

# 在指定目录工作
mcode --dir /path/to/project

# 启用详细输出
mcode --verbose
```

#### 配置文件

可以创建配置文件 `~/.minion-code/config.json` 来设置默认模型和其他选项：

```json
{
  "primary_provider": "anthropic",
  "model_profiles": [
    {
      "name": "Claude Sonnet",
      "provider": "anthropic",
      "model_name": "claude-sonnet-4-20250514",
      "api_key": "your-api-key",
      "max_tokens": 8192,
      "context_length": 200000,
      "is_active": true
    },
    {
      "name": "GPT-4o",
      "provider": "openai",
      "model_name": "gpt-4o",
      "api_key": "your-api-key",
      "max_tokens": 4096,
      "context_length": 128000,
      "is_active": true
    }
  ],
  "model_pointers": {
    "main": "claude-sonnet-4-20250514",
    "quick": "claude-haiku-20250305",
    "task": "claude-sonnet-4-20250514",
    "reasoning": "o1-mini"
  },
  "default_model_name": "claude-sonnet-4-20250514"
}
```

### 模型别名

minion-code 提供了便捷的模型别名：

| 别名 | 实际模型 | 提供商 |
|------|---------|--------|
| `sonnet` | claude-sonnet-4-20250514 | Anthropic |
| `haiku` | claude-haiku-20250305 | Anthropic |
| `opus` | claude-opus-4-20250514 | Anthropic |
| `gpt-4o` | gpt-4o | OpenAI |
| `gpt-4o-mini` | gpt-4o-mini | OpenAI |
| `o1-mini` | o1-mini | OpenAI |
| `o4-mini` | o4-mini | OpenAI |

### GPT-5 特殊配置

如果使用 GPT-5 模型，系统会自动进行配置优化：

- 自动设置 `reasoning_effort`（默认 'medium'）
- 自动调整 `context_length`（最小 128k）
- 自动调整 `max_tokens`（最小 8192）
- 自动设置 `base_url`（默认 'https://api.openai.com/v1'）

```python
# GPT-5 会被自动检测并配置
agent = await MinionCodeAgent.create(
    name="GPT-5 Assistant",
    llm="gpt-5-preview"
)
```

## 高级配置

### 自定义 API 端点

对于自定义部署或代理，可以指定 `base_url`：

```json
{
  "model_profiles": [
    {
      "name": "Custom GPT",
      "provider": "custom-openai",
      "model_name": "gpt-4o",
      "api_key": "your-api-key",
      "base_url": "https://your-custom-endpoint.com/v1",
      "max_tokens": 4096,
      "context_length": 128000
    }
  ]
}
```

### 代理配置

如果需要通过代理访问 API：

```json
{
  "proxy": "http://your-proxy-server:port"
}
```

或者通过环境变量：

```bash
export HTTP_PROXY="http://your-proxy-server:port"
export HTTPS_PROXY="https://your-proxy-server:port"
```

### 上下文窗口管理

minion-code 具有自动压缩对话历史的功能，以避免超出上下文限制：

```python
agent = await MinionCodeAgent.create(name="Assistant", llm="sonnet")

# 获取上下文使用统计
stats = agent.get_context_stats()
print(f"Token 使用: {stats['total_tokens']}/{stats['remaining_tokens']}")
print(f"使用率: {stats['usage_percentage']:.1%}")

# 手动触发压缩
if stats['needs_compacting']:
    agent.force_compact_history()

# 更新压缩配置
agent.update_compact_config(
    context_window=200000,    # 上下文窗口大小
    compact_threshold=0.92,   # 触发压缩的阈值 (92%)
    preserve_recent_messages=10,  # 保留最近的消息数
    compression_ratio=0.5     # 压缩比例
)
```

## 故障排除

### 1. API Key 未设置

**错误信息：**
```
Error: ANTHROPIC_API_KEY not found in environment
```

**解决方法：**
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

### 2. MINION_ROOT 未找到

**错误信息：**
```
Error: Could not locate MINION_ROOT
```

**解决方法：**
确保正确安装了 minion 依赖：
```bash
pip install minionx
# 或者
pip install -e ../minion
```

### 3. 模型不可用

**错误信息：**
```
Error: Model 'xxx' not found or not accessible
```

**解决方法：**
- 检查 API Key 是否正确
- 确认模型名称是否正确
- 检查账户是否有权限访问该模型

### 4. 上下文长度超限

**错误信息：**
```
Error: Context length exceeded
```

**解决方法：**
```python
# 手动触发历史压缩
agent.force_compact_history()

# 或者调整自动压缩配置
agent.update_compact_config(compact_threshold=0.85)
```

## 参考资源

- [Minion 框架文档](https://github.com/femto/minion)
- [Anthropic API 文档](https://docs.anthropic.com/)
- [OpenAI API 文档](https://platform.openai.com/docs)
- [MCP 工具集成指南](docs/MCP_GUIDE.md)
- [主 README](README.md)
