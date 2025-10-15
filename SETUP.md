# Minion Code 设置指南

## 环境设置

由于项目依赖于 minion 框架，需要正确设置 Python 路径。

### 方法 1: 使用环境脚本

```bash
# 激活虚拟环境
source .venv/bin/activate

# 设置环境变量
source setup_env.sh

# 现在可以正常使用
python -c "from minion_code.tools import FileReadTool; print('工具导入成功')"
```

### 方法 2: 手动设置 PYTHONPATH

```bash
# 激活虚拟环境
source .venv/bin/activate

# 设置 PYTHONPATH
export PYTHONPATH="/Users/femtozheng/python-project/minion1:$PYTHONPATH"

# 使用工具
python -c "from minion_code.tools import FileReadTool; print('工具导入成功')"
```

## 工具结构

项目现在使用模块化的工具结构，每个工具都在单独的文件中：

```
minion_code/tools/
├── __init__.py                    # 工具导入和映射
├── file_read_tool.py             # 文件读取工具
├── file_write_tool.py            # 文件写入工具
├── bash_tool.py                  # Bash 命令执行工具
├── grep_tool.py                  # 文本搜索工具
├── glob_tool.py                  # 文件模式匹配工具
├── ls_tool.py                    # 目录列表工具
└── python_interpreter_tool.py    # Python 代码执行工具
```

## 运行测试

```bash
# 激活环境并运行测试
source .venv/bin/activate
python -m pytest tests/ -v
```

## 使用示例

```python
# 设置环境后，可以正常导入和使用工具
from minion_code.tools import FileReadTool, FileWriteTool, BashTool

# 创建工具实例
file_reader = FileReadTool()
file_writer = FileWriteTool()
bash_tool = BashTool()

# 使用工具
content = file_reader.forward("example.txt")
file_writer.forward("output.txt", "Hello, World!")
result = bash_tool.forward("ls -la")
```

## 注意事项

1. 所有工具现在都继承自 `minion.tools.BaseTool`
2. 需要正确设置 PYTHONPATH 以访问 minion 框架
3. 测试文件已经包含了必要的路径设置