from rich.console import Console
from rich.text import Text

# 创建一个控制台对象
console = Console()

# 使用print方法直接输出带颜色的文本
console.print("这是[red]红色[/red]文本")
console.print("这是[blue]蓝色[/blue]文本")
console.print("这是[green]绿色[/green]文本")

# 背景色
console.print("[on red]红色背景[/on red]")

# 使用RGB真彩色
console.print("[rgb(255,105,180)]粉红色文本[/rgb(255,105,180)]")
console.print("[italic]Just type your message to chat with the AI agent![/italic]")

# 使用Text对象创建更复杂的格式
text = Text()
text.append("彩虹文本: ")
text.append("红", style="red")
text.append("橙", style="orange1")
text.append("黄", style="yellow")
text.append("绿", style="green")
text.append("蓝", style="blue")
text.append("靛", style="indigo")
text.append("紫", style="violet")
console.print(text)