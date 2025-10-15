#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
异步工具使用示例
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from minion_code.tools import AsyncBaseTool, async_tool, SyncToAsyncToolAdapter, FileReadTool


# 使用装饰器创建异步工具
@async_tool
async def async_web_request(url: str) -> str:
    """
    异步网络请求工具
    
    Args:
        url: 要请求的URL
        
    Returns:
        请求结果
    """
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                content = await response.text()
                return f"状态码：{response.status}\n内容长度：{len(content)} 字符\n内容预览：{content[:200]}..."
    except Exception as e:
        return f"请求失败：{str(e)}"


# 创建自定义异步工具类
class AsyncFileProcessTool(AsyncBaseTool):
    """异步文件处理工具"""
    
    name = "async_file_process"
    description = "异步处理文件内容"
    inputs = {
        "file_path": {"type": "string", "description": "文件路径"},
        "operation": {"type": "string", "description": "操作类型：count_lines, count_words, uppercase"}
    }
    output_type = "string"
    
    async def forward(self, file_path: str, operation: str) -> str:
        """异步处理文件"""
        try:
            # 模拟异步文件读取
            await asyncio.sleep(0.1)  # 模拟I/O延迟
            
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            if operation == "count_lines":
                lines = content.count('\n') + 1
                return f"文件 {file_path} 共有 {lines} 行"
            elif operation == "count_words":
                words = len(content.split())
                return f"文件 {file_path} 共有 {words} 个单词"
            elif operation == "uppercase":
                # 模拟处理时间
                await asyncio.sleep(0.2)
                return f"文件 {file_path} 转换为大写后的前100个字符：\n{content[:100].upper()}"
            else:
                return f"不支持的操作：{operation}"
                
        except Exception as e:
            return f"处理文件时出错：{str(e)}"


async def main():
    """异步工具使用演示"""
    
    print("=== 异步工具使用示例 ===\n")
    
    # 1. 使用装饰器创建的异步工具
    print("1. 异步网络请求工具演示")
    web_tool = async_web_request
    try:
        result = await web_tool("https://httpbin.org/json")
        print(f"网络请求结果：\n{result}\n")
    except Exception as e:
        print(f"网络请求失败（可能需要安装aiohttp）：{e}\n")
    
    # 2. 自定义异步工具类
    print("2. 异步文件处理工具演示")
    
    # 先创建一个测试文件
    test_content = """这是一个测试文件
包含多行内容
用于演示异步文件处理工具
Hello World
Python Async Tools"""
    
    with open("async_test.txt", "w", encoding="utf-8") as f:
        f.write(test_content)
    
    async_file_tool = AsyncFileProcessTool()
    
    # 并发执行多个操作
    tasks = [
        async_file_tool("async_test.txt", "count_lines"),
        async_file_tool("async_test.txt", "count_words"),
        async_file_tool("async_test.txt", "uppercase")
    ]
    
    results = await asyncio.gather(*tasks)
    
    for i, result in enumerate(results, 1):
        print(f"操作 {i} 结果：{result}")
    
    print()
    
    # 3. 同步工具转异步适配器
    print("3. 同步工具转异步适配器演示")
    sync_read_tool = FileReadTool()
    async_read_tool = SyncToAsyncToolAdapter(sync_read_tool)
    
    result = await async_read_tool("async_test.txt")
    print(f"异步读取结果：\n{result}\n")
    
    # 清理测试文件
    try:
        os.remove("async_test.txt")
        print("清理测试文件完成")
    except:
        pass


if __name__ == "__main__":
    asyncio.run(main())