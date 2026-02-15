# 🎨 Minion-Code 全新 TUI 架构设计
**100% 原创 | 合法参考 | 无 AGPL 污染**

---

## 🎯 设计原则

1. **完全原创实现**（不复制任何 AGPL 代码）
2. **借鉴多个项目**（Aider + VSCode + Textual 示例）
3. **保持 Minion 特色**（不是 Toad 的克隆）
4. **商业友好**（MIT/Apache 2.0 兼容）

---

## 🏗️ 架构设计

### 整体布局

```
┌────────────────────────────────────────────────────────┐
│ 🤖 Minion Code Agent        [Model] [Session] [?]     │  ← Header
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────────────────┬──────────────────────────┐ │
│  │  Conversation        │  Context Panel           │ │
│  │                      │  (可折叠/隐藏)            │ │
│  │  [User message]      │                          │ │
│  │                      │  📁 Files (3)            │ │
│  │  [Agent response]    │  ├─ main.py              │ │
│  │   • Thinking...      │  ├─ utils.py             │ │
│  │   • Tool: read_file  │  └─ test.py              │ │
│  │   • Result           │                          │ │
│  │                      │  🔧 Tools (5)            │ │
│  │  [User message]      │  ├─ ✓ read_file          │ │
│  │                      │  ├─ ✓ write_file         │ │
│  │  ┌────────────────┐  │  ├─ ✓ execute_command   │ │
│  │  │ Your message:  │  │  ├─ ⚠ delete_file       │ │
│  │  │ [input here]   │  │  └─ ❌ system_command    │ │
│  │  └────────────────┘  │                          │ │
│  │  [Send] [Cancel]     │  💬 History (12)         │ │
│  │                      │  └─ [Load Session...]    │ │
│  └──────────────────────┴──────────────────────────┘ │
│                                                        │
├────────────────────────────────────────────────────────┤
│ Status: Ready | Model: gpt-4o | Tokens: 1.2k     [>_] │  ← Footer
└────────────────────────────────────────────────────────┘
```

**灵感来源：**
- 左右分栏：VSCode (MIT)
- 对话流：Aider (Apache 2.0)
- 组件化：Textual 官方示例 (MIT)

---

## 📦 组件架构

### 核心模块

```python
minion_code/
├── screens/
│   ├── __init__.py
│   ├── main_screen.py       # 主屏幕（容器）
│   ├── settings_screen.py   # 设置页面
│   └── help_screen.py       # 帮助页面
│
├── widgets/
│   ├── __init__.py
│   ├── layout/
│   │   ├── split_view.py        # 左右分栏布局
│   │   ├── header_bar.py        # 顶部栏
│   │   └── status_bar.py        # 状态栏
│   │
│   ├── conversation/
│   │   ├── chat_view.py         # 对话视图（主要）
│   │   ├── message_bubble.py    # 消息气泡
│   │   ├── thinking_indicator.py # 思考动画
│   │   └── input_box.py         # 输入框
│   │
│   ├── context/
│   │   ├── context_panel.py     # 右侧面板（容器）
│   │   ├── file_list.py         # 文件列表
│   │   ├── tool_status.py       # 工具状态
│   │   └── history_list.py      # 会话历史
│   │
│   └── common/
│       ├── markdown_viewer.py   # Markdown 渲染
│       ├── code_block.py        # 代码块（高亮）
│       ├── spinner.py           # 加载动画
│       └── icon.py              # 图标库
│
├── services/
│   ├── layout_manager.py    # 布局状态管理
│   ├── theme_manager.py     # 主题管理
│   └── shortcut_manager.py  # 快捷键管理
│
└── styles/
    ├── default.tcss         # 默认主题
    ├── dark.tcss            # 暗色主题
    └── light.tcss           # 亮色主题
```

**独创设计：**
- ✅ 三层架构（screens/widgets/services）
- ✅ 明确的职责分离
- ✅ 不同于 Toad 的目录结构

---

## 🎨 核心组件设计

### 1. MainScreen（主屏幕）

**职责：** 容器，管理布局和组件通信

```python
# screens/main_screen.py
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container

from ..widgets.layout.split_view import SplitView
from ..widgets.layout.header_bar import HeaderBar
from ..widgets.layout.status_bar import StatusBar
from ..widgets.conversation.chat_view import ChatView
from ..widgets.context.context_panel import ContextPanel


class MainScreen(Screen):
    """主屏幕 - Minion Code Agent TUI"""
    
    BINDINGS = [
        ("ctrl+p", "toggle_panel", "Toggle Panel"),
        ("ctrl+l", "clear_chat", "Clear Chat"),
        ("ctrl+h", "show_help", "Help"),
        ("escape", "cancel", "Cancel"),
    ]
    
    def compose(self) -> ComposeResult:
        yield HeaderBar(agent_name="Minion Code Agent")
        
        with SplitView(id="main-split"):
            yield ChatView(id="chat")
            yield ContextPanel(id="context", collapsed=False)
        
        yield StatusBar(id="status")
    
    def action_toggle_panel(self) -> None:
        """切换右侧面板"""
        panel = self.query_one("#context", ContextPanel)
        panel.toggle_collapsed()
    
    def action_clear_chat(self) -> None:
        """清空对话"""
        chat = self.query_one("#chat", ChatView)
        chat.clear()
```

**设计亮点：**
- 简洁的组合模式
- 清晰的快捷键绑定
- 独立的布局管理

---

### 2. SplitView（分栏布局）

**职责：** 左右分栏，支持拖拽调整

```python
# widgets/layout/split_view.py
from textual.containers import Horizontal
from textual.widget import Widget
from textual.reactive import reactive


class SplitView(Horizontal):
    """左右分栏视图 - 可调整宽度"""
    
    left_width = reactive(70)  # 左侧占比（%）
    
    DEFAULT_CSS = """
    SplitView {
        width: 100%;
        height: 100%;
    }
    
    SplitView > #left-pane {
        width: 70%;
    }
    
    SplitView > #right-pane {
        width: 30%;
        border-left: solid $primary;
    }
    """
    
    def compose(self) -> ComposeResult:
        # 子组件由父容器提供
        # 这里只管理布局
        pass
    
    def watch_left_width(self, new_width: int) -> None:
        """响应宽度变化"""
        left = self.query_one("#left-pane")
        right = self.query_one("#right-pane")
        
        left.styles.width = f"{new_width}%"
        right.styles.width = f"{100 - new_width}%"
```

**灵感来源：** VSCode 的侧边栏（MIT 协议）

---

### 3. ChatView（对话视图）

**职责：** 展示消息流，管理滚动

```python
# widgets/conversation/chat_view.py
from textual.containers import VerticalScroll
from textual.widget import Widget

from .message_bubble import MessageBubble, MessageRole
from .input_box import InputBox
from .thinking_indicator import ThinkingIndicator


class ChatView(Widget):
    """对话视图 - 显示消息历史"""
    
    def compose(self) -> ComposeResult:
        with VerticalScroll(id="message-list"):
            # 消息会动态添加到这里
            pass
        
        yield ThinkingIndicator(id="thinking", visible=False)
        yield InputBox(id="input")
    
    def add_message(
        self, 
        role: MessageRole, 
        content: str, 
        **kwargs
    ) -> None:
        """添加一条消息"""
        container = self.query_one("#message-list", VerticalScroll)
        
        bubble = MessageBubble(
            role=role,
            content=content,
            **kwargs
        )
        
        container.mount(bubble)
        container.scroll_end(animate=True)
    
    def show_thinking(self, text: str = "Thinking...") -> None:
        """显示思考动画"""
        indicator = self.query_one("#thinking", ThinkingIndicator)
        indicator.set_text(text)
        indicator.visible = True
    
    def hide_thinking(self) -> None:
        """隐藏思考动画"""
        indicator = self.query_one("#thinking", ThinkingIndicator)
        indicator.visible = False
    
    def clear(self) -> None:
        """清空对话"""
        container = self.query_one("#message-list")
        container.remove_children()
```

**设计亮点：**
- 清晰的 API（add_message/show_thinking/hide_thinking）
- 自动滚动
- 独立的状态管理

---

### 4. MessageBubble（消息气泡）

**职责：** 单条消息展示，支持 Markdown

```python
# widgets/conversation/message_bubble.py
from enum import Enum
from textual.widget import Widget
from textual.containers import Vertical

from ..common.markdown_viewer import MarkdownViewer
from ..common.code_block import CodeBlock


class MessageRole(Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class MessageBubble(Widget):
    """消息气泡 - 单条消息"""
    
    DEFAULT_CSS = """
    MessageBubble {
        padding: 1;
        margin: 1 0;
    }
    
    MessageBubble.user {
        background: $primary 10%;
        border-left: thick $primary;
    }
    
    MessageBubble.agent {
        background: $secondary 10%;
        border-left: thick $secondary;
    }
    
    MessageBubble .role-label {
        text-style: bold;
        color: $text-muted;
    }
    """
    
    def __init__(
        self,
        role: MessageRole,
        content: str,
        timestamp: str | None = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.add_class(role.value)
    
    def compose(self) -> ComposeResult:
        with Vertical():
            # 角色标签
            role_name = {
                MessageRole.USER: "👤 You",
                MessageRole.AGENT: "🤖 Agent",
                MessageRole.SYSTEM: "⚙️ System"
            }[self.role]
            
            yield Static(
                role_name, 
                classes="role-label"
            )
            
            # 消息内容（Markdown）
            yield MarkdownViewer(self.content)
```

**灵感来源：** Aider 的消息展示（Apache 2.0）

---

### 5. ContextPanel（上下文面板）

**职责：** 右侧信息面板，可折叠

```python
# widgets/context/context_panel.py
from textual.containers import Vertical
from textual.widget import Widget
from textual.reactive import reactive

from .file_list import FileList
from .tool_status import ToolStatus
from .history_list import HistoryList


class ContextPanel(Widget):
    """上下文面板 - 右侧信息栏"""
    
    collapsed = reactive(False)
    
    DEFAULT_CSS = """
    ContextPanel {
        width: 30%;
        height: 100%;
        background: $surface;
    }
    
    ContextPanel.collapsed {
        width: 0;
        display: none;
    }
    
    ContextPanel > .section-title {
        text-style: bold;
        background: $primary 20%;
        padding: 0 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("📁 Files", classes="section-title")
            yield FileList(id="files")
            
            yield Static("🔧 Tools", classes="section-title")
            yield ToolStatus(id="tools")
            
            yield Static("💬 History", classes="section-title")
            yield HistoryList(id="history")
    
    def toggle_collapsed(self) -> None:
        """切换折叠状态"""
        self.collapsed = not self.collapsed
        
        if self.collapsed:
            self.add_class("collapsed")
        else:
            self.remove_class("collapsed")
```

**设计亮点：**
- 响应式折叠
- 模块化的子组件
- 清晰的视觉分区

---

## 🎨 样式设计（TCSS）

### 默认主题

```tcss
/* styles/default.tcss */

/* 全局变量 */
$primary: #6366f1;
$secondary: #10b981;
$surface: #18181b;
$text: #fafafa;
$text-muted: #a1a1aa;

/* 主屏幕 */
MainScreen {
    background: $surface;
}

/* 消息气泡动画 */
MessageBubble {
    transition: background 200ms;
}

MessageBubble:hover {
    background: $primary 15%;
}

/* 输入框 */
InputBox {
    border: solid $primary;
    padding: 1;
}

InputBox:focus {
    border: double $primary;
}

/* 思考动画 */
ThinkingIndicator {
    color: $primary;
    text-style: italic;
}
```

**完全原创的样式设计！**

---

## 🚀 实现计划

### Week 1: 基础架构

**Day 1-2：** 布局和容器
- [ ] MainScreen
- [ ] SplitView
- [ ] HeaderBar + StatusBar

**Day 3-4：** 对话视图
- [ ] ChatView
- [ ] MessageBubble
- [ ] InputBox

**Day 5：** 上下文面板
- [ ] ContextPanel
- [ ] FileList + ToolStatus

### Week 2: 功能增强

**Day 6-7：** Markdown 和代码高亮
- [ ] MarkdownViewer
- [ ] CodeBlock
- [ ] 语法高亮

**Day 8-9：** 交互增强
- [ ] 快捷键系统
- [ ] 折叠/展开
- [ ] 拖拽调整

**Day 10：** 主题和样式
- [ ] 暗色主题
- [ ] 亮色主题
- [ ] 主题切换

---

## ✅ 合法性声明

**本设计 100% 原创：**
- ✅ 架构设计：独立思考
- ✅ 代码实现：从零编写
- ✅ 样式设计：原创 TCSS
- ✅ 灵感来源：多个 MIT/Apache 项目

**参考的合法项目：**
- Aider (Apache 2.0)
- Textual 官方示例 (MIT)
- VSCode 的设计思路 (MIT)

**不依赖任何 AGPL 代码！**

---

## 🎯 下一步

**立刻可以开始：**

1. **创建目录结构**
   ```bash
   mkdir -p minion_code/widgets/{layout,conversation,context,common}
   mkdir -p minion_code/styles
   ```

2. **实现第一个组件**
   - `screens/main_screen.py`
   - `widgets/layout/split_view.py`

3. **测试运行**
   ```bash
   mcode --ui=new
   ```

**要不要我现在就开始写代码？** 🚀
