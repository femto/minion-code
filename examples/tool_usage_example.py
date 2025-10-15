#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工具使用示例
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from minion_code.tools import (
    FileReadTool,
    FileWriteTool,
    BashTool,
    GrepTool,
    GlobTool,
    LsTool,
    PythonInterpreterTool
)


def main():
    """演示各种工具的使用"""
    
    print("=== Minion Code Tools 使用示例 ===\n")
    
    # 1. 文件写入工具
    print("1. 文件写入工具演示")
    write_tool = FileWriteTool()
    result = write_tool("test_file.txt", "Hello, Minion Code Tools!\n这是一个测试文件。")
    print(f"写入结果：{result}\n")
    
    # 2. 文件读取工具
    print("2. 文件读取工具演示")
    read_tool = FileReadTool()
    result = read_tool("test_file.txt")
    print(f"读取结果：\n{result}\n")
    
    # 3. 目录列表工具
    print("3. 目录列表工具演示")
    ls_tool = LsTool()
    result = ls_tool(".")
    print(f"目录内容：\n{result}\n")
    
    # 4. Glob工具
    print("4. Glob工具演示")
    glob_tool = GlobTool()
    result = glob_tool("*.py")
    print(f"Python文件：\n{result}\n")
    
    # 5. Grep工具
    print("5. Grep工具演示")
    grep_tool = GrepTool()
    result = grep_tool("import", ".", "*.py")
    print(f"搜索结果：\n{result}\n")
    
    # 6. Python解释器工具
    print("6. Python解释器工具演示")
    python_tool = PythonInterpreterTool()
    code = """
import math
print("计算圆的面积：")
radius = 5
area = math.pi * radius ** 2
print(f"半径为 {radius} 的圆的面积是：{area:.2f}")
"""
    result = python_tool(code)
    print(f"Python执行结果：\n{result}\n")
    
    # 7. Bash工具（安全命令）
    print("7. Bash工具演示")
    bash_tool = BashTool()
    result = bash_tool("echo 'Hello from bash!'")
    print(f"Bash执行结果：\n{result}\n")
    
    # 清理测试文件
    try:
        os.remove("test_file.txt")
        print("清理测试文件完成")
    except:
        pass


if __name__ == "__main__":
    main()