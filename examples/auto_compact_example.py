#!/usr/bin/env python3
"""
Example: Using AUTO_COMPACT with MinionCodeAgent

This example demonstrates how the AUTO_COMPACT feature automatically
manages context window usage in long conversations.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from minion_code.agents.code_agent import MinionCodeAgent


async def demo_auto_compact():
    """Demonstrate AUTO_COMPACT functionality"""
    print("🤖 Creating MinionCodeAgent with AUTO_COMPACT...")
    
    # Create agent with default AUTO_COMPACT settings
    agent = await MinionCodeAgent.create(
        name="Auto-Compact Demo Agent",
        llm="gpt-4o-mini"
    )
    
    print("✅ Agent created with AUTO_COMPACT enabled")
    print(f"📊 Context window: {agent.auto_compact.config.context_window:,} tokens")
    print(f"🚨 Compact threshold: {agent.auto_compact.config.compact_threshold:.0%}")
    print(f"💾 Preserve recent: {agent.auto_compact.config.preserve_recent_messages} messages")
    
    # Show initial context stats
    stats = agent.get_context_stats()
    print(f"\n📈 Initial context usage:")
    print(f"  Total tokens: {stats['total_tokens']:,}")
    print(f"  Usage: {stats['usage_percentage']:.1%}")
    print(f"  Remaining: {stats['remaining_tokens']:,} tokens")
    
    # Simulate adding many messages to trigger compaction
    print(f"\n🔄 Simulating long conversation...")
    
    # Add messages directly to history to simulate a long conversation
    for i in range(50):
        # Add user message
        agent.state.history.append({
            'role': 'user',
            'content': f'User message {i+1}: ' + 'This is a long message with lots of content. ' * 20
        })
        
        # Add assistant message
        agent.state.history.append({
            'role': 'assistant', 
            'content': f'''Assistant response {i+1}:

```python
def example_function_{i}():
    """Example function number {i}"""
    result = []
    for j in range(100):
        if j % 2 == 0:
            result.append(f"Even number: {{j}}")
        else:
            result.append(f"Odd number: {{j}}")
    return result

class ExampleClass_{i}:
    def __init__(self, value):
        self.value = value
        self.data = [x for x in range(value)]
    
    def process(self):
        return sum(self.data) * self.value
```

This code demonstrates various programming concepts including loops, conditionals, list comprehensions, and class definitions. The function processes numbers and the class manages data structures.
'''
        })
    
    # Check context stats after adding messages
    stats = agent.get_context_stats()
    print(f"\n📈 Context usage after adding messages:")
    print(f"  Messages: {len(agent.state.history)}")
    print(f"  Total tokens: {stats['total_tokens']:,}")
    print(f"  Usage: {stats['usage_percentage']:.1%}")
    print(f"  Needs compacting: {stats['needs_compacting']}")
    
    # Trigger pre_step to activate AUTO_COMPACT
    if stats['needs_compacting']:
        print(f"\n🔄 Triggering AUTO_COMPACT via pre_step...")
        await agent.pre_step("test input", {})
        
        # Check stats after compaction
        new_stats = agent.get_context_stats()
        print(f"\n📈 Context usage after AUTO_COMPACT:")
        print(f"  Messages: {len(agent.state.history)} (was {stats['total_tokens'] // 100})")  # Rough estimate
        print(f"  Total tokens: {new_stats['total_tokens']:,} (was {stats['total_tokens']:,})")
        print(f"  Usage: {new_stats['usage_percentage']:.1%} (was {stats['usage_percentage']:.1%})")
        print(f"  Needs compacting: {new_stats['needs_compacting']}")
        
        # Show compression summary
        compression_ratio = new_stats['total_tokens'] / stats['total_tokens']
        print(f"  Compression ratio: {compression_ratio:.1%}")
    else:
        print(f"\n✅ No compaction needed yet")
    
    # Demonstrate manual compaction
    print(f"\n🔧 Testing manual compaction...")
    compacted = agent.force_compact_history()
    if compacted:
        print(f"✅ Manual compaction successful")
    else:
        print(f"ℹ️ No compaction needed")
    
    # Show final stats
    final_stats = agent.get_context_stats()
    print(f"\n📊 Final context stats:")
    print(f"  Messages: {len(agent.state.history)}")
    print(f"  Total tokens: {final_stats['total_tokens']:,}")
    print(f"  Usage: {final_stats['usage_percentage']:.1%}")
    
    # Demonstrate config updates
    print(f"\n⚙️ Updating AUTO_COMPACT configuration...")
    agent.update_compact_config(
        compact_threshold=0.85,  # Change threshold to 85%
        preserve_recent_messages=15  # Keep more recent messages
    )
    print(f"✅ Configuration updated")
    
    print(f"\n🎉 AUTO_COMPACT demo completed!")


if __name__ == "__main__":
    asyncio.run(demo_auto_compact())