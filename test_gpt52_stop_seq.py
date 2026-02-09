"""Test script to reproduce gpt-5.2 stop sequence bug on Azure"""
import asyncio
import sys
sys.path.insert(0, '/Users/femtozheng/python-project/minion1')

from minion.configs.config import config
from minion.models.llm_client import LLMClient

async def test_gpt52():
    # Load config
    config.load_config('/Users/femtozheng/python-project/minion1/config/config.yaml')

    # Test with stop sequence
    client = LLMClient(config_name="gpt-5.2")

    print("=" * 60)
    print("Testing gpt-5.2 with stop sequence")
    print("=" * 60)

    # Test cases that might trigger stop sequence issues
    test_messages = [
        [{"role": "user", "content": "Say hello and stop after 'world'."}],
        [{"role": "user", "content": "Count from 1 to 5, one number per line."}],
    ]

    stop_sequences = [
        ["world"],
        ["\n\n"],
        ["5"],
    ]

    for messages in test_messages:
        for stop in stop_sequences:
            print(f"\n--- Test: {messages[0]['content'][:40]}... | stop={stop} ---")
            try:
                response = await client.chat_completion(
                    messages=messages,
                    stop=stop,
                    max_tokens=100
                )
                print(f"Response: {response}")
            except Exception as e:
                print(f"ERROR: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_gpt52())
