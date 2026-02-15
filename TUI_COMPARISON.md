# 🎨 TUI 对比：Minion-Code vs Toad

## 📊 项目概览

### Minion-Code（当前）
- **路径：** `/Users/femtozheng/python-project/minion-code/`
- **TUI 实现：** `minion_code/screens/REPL.py`
- **框架：** Textual
- **风格：** 简单的 REPL 风格，单文件实现

### Toad（参考目标）
- **路径：** `/Users/femtozheng/python-project/toad/`
- **TUI 实现：** `src/toad/screens/main.py` + 多个 widget
- **框架：** Textual（高级）
- **风格：** 完整的 IDE 风格，模块化架构

---

## 🔍 架构对比

### Minion-Code 架构（简单）

```
minion_code/
├── screens/
│   └── REPL.py          # 单文件包含所有 UI
└── cli.py               # 命令行入口
```

**特点：**
- ✅ 简单直接
- ✅ 快速启动
- ❌ 单文件 1900+ 行，难以维护
- ❌ 组件耦合严重

### Toad 架构（模块化）

```
src/toad/
├── screens/
│   ├── main.py          # 主屏幕（入口）
│   ├── settings.py      # 设置屏幕
│   └── permissions.py   # 权限管理
├── widgets/
│   ├── conversation.py  # 对话组件（核心）
│   ├── prompt.py        # 输入框
│   ├── agent_response.py # Agent 回复
│   ├── agent_thought.py  # Agent 思考过程
│   ├── terminal.py      # 终端组件
│   ├── side_bar.py      # 侧边栏
│   ├── project_directory_tree.py  # 文件树
│   └── ...              # 30+ 个独立组件
├── app.py               # 应用主类
└── cli.py               # 命令行入口
```

**特点：**
- ✅ 高度模块化
- ✅ 易于维护和扩展
- ✅ 组件复用
- ✅ 清晰的职责分离

---

## 🎯 核心功能对比

### 1. 对话界面

#### Minion-Code
```python
class REPL(Screen):
    # 包含所有功能：
    # - Logo
    # - 消息列表
    # - 输入框
    # - 按钮
    # - 状态显示
    # 全部在一个类里
```

**问题：**
- 所有逻辑混在一起
- 难以测试单个组件
- 代码重复

#### Toad
```python
# screens/main.py
class MainScreen(Screen):
    conversation = getters.query_one(Conversation)
    side_bar = getters.query_one(SideBar)
    project_directory_tree = getters.query_one("#project_directory_tree")

# widgets/conversation.py
class Conversation(Widget):
    # 只负责对话逻辑
    prompt = getters.query_one(Prompt)
    terminal = getters.query_one(Terminal)
    
    def compose(self) -> ComposeResult:
        yield containers.Vertical(
            Prompt(),
            UserInput(),
            AgentResponse(),
            Terminal()
        )
```

**优点：**
- 每个组件独立
- 可以单独测试
- 易于扩展

---

### 2. 核心组件拆分

| 功能 | Minion-Code | Toad |
|------|-------------|------|
| **对话展示** | `REPL.py` (内联) | `conversation.py` |
| **输入框** | `REPL.py` (内联) | `prompt.py` + `user_input.py` |
| **Agent 回复** | `REPL.py` (内联) | `agent_response.py` + `agent_thought.py` |
| **终端** | 无 | `terminal.py` + `shell_terminal.py` |
| **侧边栏** | 无 | `side_bar.py` |
| **文件树** | 无 | `project_directory_tree.py` |
| **命令面板** | 无 | `command_pane.py` |
| **Markdown 渲染** | 基础 | `markdown_note.py` + 高亮 |
| **工具调用显示** | 简单文本 | `tool_call.py` (富文本) |

---

### 3. 高级功能

#### Toad 独有功能

##### A. 侧边栏（SideBar）
```python
class SideBar(Widget):
    # 显示：
    # - 文件树
    # - Agent 信息
    # - 历史会话
    # - 快捷操作
```

##### B. 项目文件树
```python
class ProjectDirectoryTree(DirectoryTree):
    # 功能：
    # - 浏览项目文件
    # - 右键菜单
    # - 文件监控（实时更新）
```

##### C. 交互式终端
```python
class Terminal(Widget):
    # 功能：
    # - 运行命令
    # - 实时输出
    # - 多终端标签
    # - 命令历史
```

##### D. Agent 思考过程可视化
```python
class AgentThought(Widget):
    # 显示：
    # - 推理步骤
    # - 工具调用
    # - 决策过程
```

##### E. 权限管理
```python
class PermissionsScreen(Screen):
    # 功能：
    # - 工具权限控制
    # - 危险操作确认
    # - 审批流程
```

---

## 🛠️ 建议改造方案

### Phase 1: 基础重构（1-2 天）

#### 1.1 拆分核心组件

```python
# 目标结构
minion_code/
├── screens/
│   ├── main.py          # 主屏幕（简化）
│   └── settings.py      # 设置屏幕
├── widgets/
│   ├── conversation.py  # 对话容器
│   ├── message_list.py  # 消息列表
│   ├── prompt.py        # 输入框
│   ├── agent_response.py # Agent 回复
│   ├── tool_display.py  # 工具调用显示
│   └── status_bar.py    # 状态栏
└── ...
```

#### 1.2 实现清单

- [ ] 创建 `widgets/` 目录
- [ ] 拆分 `REPL.py` → 多个组件
- [ ] 重构 `main.py` 作为容器
- [ ] 保持 CLI 兼容

**预计工作量：** 4-6 小时

---

### Phase 2: 增强功能（3-5 天）

#### 2.1 添加 Toad 风格的核心功能

- [ ] **侧边栏** - 文件浏览 + 会话管理
- [ ] **文件树** - 项目结构展示
- [ ] **终端集成** - 命令执行 + 输出
- [ ] **思考过程可视化** - 显示 Agent 推理
- [ ] **工具调用美化** - 富文本展示

#### 2.2 交互增强

- [ ] **命令面板** (Ctrl+P) - 快速操作
- [ ] **快捷键** - Toad 风格的键盘导航
- [ ] **主题支持** - 暗色/亮色切换
- [ ] **布局切换** - 单栏/双栏/三栏

**预计工作量：** 20-30 小时

---

### Phase 3: 高级特性（1-2 周）

#### 3.1 权限系统

参考 `toad/screens/permissions.py`：

```python
class PermissionsManager:
    # 功能：
    # - 工具分类（安全/危险/禁止）
    # - 批量审批
    # - 记住选择
    # - 审计日志
```

#### 3.2 会话管理

```python
class SessionManager:
    # 功能：
    # - 多会话切换
    # - 会话历史
    # - 搜索对话
    # - 导出/导入
```

#### 3.3 Agent 市场

```python
class AgentMarketplace:
    # 功能：
    # - 浏览 Agent
    # - 一键安装
    # - 版本管理
    # - 配置编辑
```

**预计工作量：** 40-60 小时

---

## 📋 具体组件迁移计划

### 优先级 1（必须）

#### 1. Conversation 主容器

**从：** `REPL.py` 的 `REPL` 类  
**到：** `widgets/conversation.py`

**保留功能：**
- 消息列表滚动
- 输入框
- Agent 响应

**新增功能（参考 Toad）：**
- 侧边栏集成
- 终端集成
- 文件树

---

#### 2. Prompt 输入框

**从：** `REPL.py` 的 `Input` widget  
**到：** `widgets/prompt.py`

**Toad 的优势：**
```python
class Prompt(Widget):
    # 功能：
    # - 自动补全
    # - 历史记录（上/下箭头）
    # - Slash 命令提示
    # - 语法高亮
    # - 多行编辑
```

**实现：**
```python
# widgets/prompt.py
from textual.widgets import TextArea

class Prompt(Widget):
    textarea = getters.query_one(TextArea)
    
    def compose(self) -> ComposeResult:
        yield TextArea(
            id="prompt-input",
            language="markdown",  # 语法高亮
            show_line_numbers=False,
        )
    
    def on_key(self, event) -> None:
        # 处理 Ctrl+Enter → 发送
        # 处理 Up/Down → 历史
        # 处理 / → Slash 命令
        pass
```

---

#### 3. AgentResponse 回复展示

**从：** `REPL.py` 的消息渲染  
**到：** `widgets/agent_response.py`

**Toad 的优势：**
- Markdown 渲染（代码高亮）
- 思考过程折叠/展开
- 工具调用单独显示
- 可复制代码块

**参考：**
```python
# widgets/agent_response.py
class AgentResponse(Widget):
    def compose(self) -> ComposeResult:
        yield containers.Vertical(
            Static(self.content, markup=True),  # Markdown
            AgentThought(self.reasoning),       # 思考过程
            ToolCallList(self.tool_calls),      # 工具调用
        )
```

---

### 优先级 2（重要）

#### 4. SideBar 侧边栏

**新增组件：** `widgets/side_bar.py`

**功能：**
- 文件树
- 会话历史
- Agent 信息
- 快捷操作

**布局：**
```
┌─────────────────────────────────────┐
│ [Files] [History] [Agents]          │  ← 标签切换
├─────────────────────────────────────┤
│ 📁 src/                              │
│   ├─ 📄 main.py                      │
│   ├─ 📄 utils.py                     │
│   └─ 📁 tests/                       │
│        └─ 📄 test_main.py            │
│                                      │
│ [+ New Chat] [Settings]              │
└─────────────────────────────────────┘
```

---

#### 5. Terminal 终端

**新增组件：** `widgets/terminal.py`

**功能：**
- 运行命令
- 实时输出
- ANSI 颜色支持
- 多标签

**参考 Toad：**
```python
class Terminal(Widget):
    def run_command(self, cmd: str):
        # 异步执行
        # 流式输出
        # 错误处理
```

---

### 优先级 3（增强）

#### 6. ProjectDirectoryTree 文件树

**新增组件：** `widgets/project_directory_tree.py`

**功能：**
- 目录浏览
- 文件预览
- 右键菜单
- 文件监控

---

#### 7. CommandPane 命令面板

**新增组件：** `widgets/command_pane.py`

**功能：**
- 模糊搜索
- 快捷键（Ctrl+P）
- 最近使用
- 命令分类

---

## 🎯 第一步：最小化重构

**目标：** 将 `REPL.py` 拆分成 3 个核心组件，不破坏现有功能。

### 步骤

1. **创建 widgets 目录**
   ```bash
   mkdir minion_code/widgets
   touch minion_code/widgets/__init__.py
   ```

2. **提取 Conversation 组件**
   ```python
   # widgets/conversation.py
   class Conversation(Widget):
       # 从 REPL 复制主要逻辑
       pass
   ```

3. **提取 Prompt 组件**
   ```python
   # widgets/prompt.py
   class Prompt(Widget):
       # 输入框逻辑
       pass
   ```

4. **提取 MessageList 组件**
   ```python
   # widgets/message_list.py
   class MessageList(Widget):
       # 消息展示逻辑
       pass
   ```

5. **重构 main screen**
   ```python
   # screens/main.py (新)
   class MainScreen(Screen):
       def compose(self) -> ComposeResult:
           yield Header()
           yield Conversation()
           yield Footer()
   ```

6. **保持 CLI 兼容**
   ```python
   # cli.py 不变，只改 import
   from .screens.main import MainScreen
   ```

---

## 🚀 开始行动

**立刻可以做：**

1. **分析现有代码**（30 分钟）
   - 标记 REPL.py 中的组件边界
   - 识别耦合点
   - 规划拆分顺序

2. **创建第一个组件**（1 小时）
   - 提取 Logo + StatusBar
   - 测试独立性
   - 验证不破坏功能

3. **迭代重构**（每个组件 1-2 小时）
   - 逐个组件迁移
   - 持续测试
   - 保持 git commit

---

## 💡 关键决策

### 要不要完全模仿 Toad？

**建议：** 分阶段，先基础后高级

#### Phase 1: 基础架构（必须）
- ✅ 模块化组件
- ✅ 清晰的职责分离
- ✅ 可测试性

#### Phase 2: 核心功能（重要）
- ✅ 侧边栏
- ✅ 终端集成
- ✅ 文件树

#### Phase 3: 高级特性（可选）
- ⚠️ 权限系统（看需求）
- ⚠️ Agent 市场（可延后）
- ⚠️ 多会话（可延后）

---

## 📊 代码量对比

| 项目 | 文件数 | 代码行数 | 组件数 |
|------|--------|----------|--------|
| **Minion-Code** | 1 | ~1900 | 1 (单体) |
| **Toad** | 30+ | ~5000+ | 30+ (模块化) |

**结论：** Toad 的代码量虽然更多，但**可维护性高 10 倍**。

---

## ✅ 结论

**是的，TUI 部分应该模仿 Toad！**

**原因：**
1. ✅ 架构更清晰（模块化）
2. ✅ 功能更丰富（侧边栏/终端/文件树）
3. ✅ 可维护性更强（独立组件）
4. ✅ 用户体验更好（IDE 风格）

**建议：**
- 分 3 个阶段，先基础重构，再增强功能
- 保持 CLI 兼容，渐进式迁移
- 借鉴 Toad 的架构，但保留 Minion 的特色

---

**下一步：** 要不要我帮你开始重构？我可以立刻创建第一个独立组件！🚀
