# 🤖 Claude Code Prompts for TUI Implementation

## 使用方法

1. **启动 Toad 并截图**
   ```bash
   cd ~/python-project/toad
   source .venv/bin/activate
   toad
   # 截图保存到 /tmp/toad-ui.png
   ```

2. **启动 Claude Code**
   ```bash
   cd ~/python-project/minion-code
   claude
   ```

3. **上传截图 + 使用下面的 Prompt**

---

## 📋 Prompt 1: 主界面布局

### 上传截图：Toad 主界面

```
我需要用 Textual 框架实现一个类似这个截图的 TUI 界面。

要求：
1. 使用 Textual (textual.app)
2. 左右分栏布局（70% / 30%）
3. 左侧是对话区域
4. 右侧是上下文面板（可折叠）
5. 顶部有 Header，底部有 Footer

请创建以下文件：
- minion_code/screens/main_screen.py
- minion_code/widgets/layout/split_view.py
- minion_code/widgets/layout/header_bar.py
- minion_code/widgets/layout/status_bar.py

要求代码：
- 完全原创，不复制任何现有代码
- 使用 Textual 的最佳实践
- 添加详细注释
- 包含基本的快捷键（Ctrl+P 切换面板）
```

---

## 📋 Prompt 2: 对话视图

### 上传截图：对话区域细节

```
现在实现对话视图组件，参考截图中的消息展示样式。

要求：
1. 消息气泡（区分 user/agent）
2. 滚动列表（自动滚动到底部）
3. 输入框（支持多行，Ctrl+Enter 发送）
4. "思考中..." 动画指示器

请创建：
- minion_code/widgets/conversation/chat_view.py
- minion_code/widgets/conversation/message_bubble.py
- minion_code/widgets/conversation/input_box.py
- minion_code/widgets/conversation/thinking_indicator.py

样式要求：
- User 消息：蓝色边框，左对齐
- Agent 消息：绿色边框，带角色图标
- Markdown 支持（代码块高亮）
```

---

## 📋 Prompt 3: 上下文面板

### 上传截图：右侧面板

```
实现右侧上下文面板，参考截图布局。

功能：
1. 三个折叠区域：Files / Tools / History
2. 文件列表（显示当前上下文的文件）
3. 工具状态（显示已启用/禁用的工具）
4. 会话历史（最近的对话）

请创建：
- minion_code/widgets/context/context_panel.py
- minion_code/widgets/context/file_list.py
- minion_code/widgets/context/tool_status.py
- minion_code/widgets/context/history_list.py

交互要求：
- 点击区域标题可折叠/展开
- 文件列表支持滚动
- 工具状态用图标表示（✓/⚠/❌）
```

---

## 📋 Prompt 4: Markdown 渲染

### 上传截图：代码块展示

```
实现 Markdown 内容渲染，特别是代码块高亮。

要求：
1. 支持基本 Markdown（标题、列表、粗体、斜体）
2. 代码块语法高亮（Python、JavaScript、Bash 等）
3. 可复制代码块
4. 链接可点击

请创建：
- minion_code/widgets/common/markdown_viewer.py
- minion_code/widgets/common/code_block.py

使用：
- rich.markdown.Markdown 作为基础
- Syntax highlighting 用 rich.syntax.Syntax
```

---

## 📋 Prompt 5: 样式和主题

### 上传截图：完整界面（暗色主题）

```
现在添加样式和主题支持。

请创建：
- minion_code/styles/default.tcss（TCSS 样式文件）

要求：
1. 定义颜色变量（$primary, $secondary, $surface 等）
2. 设置组件样式（边框、背景、间距）
3. 添加动画（hover 效果、过渡）
4. 响应式布局（支持不同终端大小）

参考 Textual 官方主题，但完全原创实现。
```

---

## 📋 Prompt 6: 集成和测试

```
现在把所有组件集成到一起。

任务：
1. 更新 minion_code/cli.py，添加新 UI 的启动选项
2. 实现 MainScreen 的数据流（消息传递）
3. 添加快捷键绑定
4. 编写启动脚本

请修改：
- minion_code/cli.py
- 添加 --ui=v2 选项

然后我可以这样运行：
```bash
mcode --ui=v2
```
```

---

## 🎨 进阶 Prompt（可选）

### Prompt 7: 侧边栏文件树

```
添加一个完整的文件树组件，类似 VSCode。

功能：
- 递归显示目录结构
- 展开/折叠文件夹
- 点击文件预览内容
- 右键菜单（复制路径、在编辑器打开）

文件：minion_code/widgets/sidebar/file_tree.py
```

### Prompt 8: 终端集成

```
集成一个嵌入式终端，可以执行命令。

功能：
- 运行 shell 命令
- 实时输出
- ANSI 颜色支持
- 多终端标签

文件：minion_code/widgets/terminal/terminal_view.py
```

### Prompt 9: 命令面板

```
实现一个命令面板（Ctrl+Shift+P）。

功能：
- 模糊搜索命令
- 显示快捷键
- 最近使用命令
- 命令分类

文件：minion_code/widgets/command/command_palette.py
```

---

## 🚀 快速启动脚本

保存为 `build-ui.sh`：

```bash
#!/bin/bash

echo "🎨 Building new TUI for Minion-Code"
echo ""

# 1. 截图 Toad
echo "📸 Step 1: Screenshot Toad (manual)"
echo "   cd ~/python-project/toad && source .venv/bin/activate && toad"
echo "   Take screenshots and save to /tmp/toad-ui/"
echo ""
read -p "Press Enter when screenshots are ready..."

# 2. 启动 Claude Code
echo ""
echo "🤖 Step 2: Starting Claude Code..."
cd ~/python-project/minion-code

if command -v claude &> /dev/null; then
    echo "Using Claude Code"
    claude
elif command -v codex &> /dev/null; then
    echo "Using Codex"
    codex
else
    echo "❌ Neither Claude Code nor Codex found"
    echo "Please install one of them first"
    exit 1
fi
```

---

## 📊 进度跟踪

### Phase 1: 基础布局 ✅
- [ ] MainScreen
- [ ] SplitView
- [ ] HeaderBar
- [ ] StatusBar

### Phase 2: 对话视图 ✅
- [ ] ChatView
- [ ] MessageBubble
- [ ] InputBox
- [ ] ThinkingIndicator

### Phase 3: 上下文面板 ✅
- [ ] ContextPanel
- [ ] FileList
- [ ] ToolStatus
- [ ] HistoryList

### Phase 4: Markdown & 样式 ✅
- [ ] MarkdownViewer
- [ ] CodeBlock
- [ ] TCSS 主题

### Phase 5: 集成 ✅
- [ ] CLI 集成
- [ ] 快捷键
- [ ] 测试

---

## 💡 提示

**给 Claude Code 的通用要求：**

```
所有代码要求：
1. ✅ 完全原创实现
2. ✅ 不复制任何 AGPL 代码
3. ✅ 遵循 Textual 最佳实践
4. ✅ 添加详细注释
5. ✅ 类型提示（type hints）
6. ✅ 错误处理
7. ✅ 响应式布局

代码风格：
- 使用 Black 格式化
- 遵循 PEP 8
- 清晰的变量命名
- 模块化设计
```

---

## 🎯 预期结果

完成后，你会有：
- ✅ 一个漂亮的 TUI 界面
- ✅ 100% 原创代码（合法）
- ✅ 借鉴了 Toad 的设计（但不侵权）
- ✅ 模块化架构（易于维护）
- ✅ 商业友好（MIT/Apache 兼容）

**预计时间：** 2-4 小时（Claude Code 自动生成）

**手动工作：** 截图 + 粘贴 Prompt + 测试

完全可行！🚀
