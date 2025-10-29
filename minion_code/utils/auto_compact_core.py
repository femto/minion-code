#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto Compact Core - Token management and history compression

This module provides functionality to:
1. Calculate token counts for messages
2. Monitor context window usage  
3. Automatically compress history when approaching limits
"""

import re
import hashlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class CompactConfig:
    """Configuration for auto-compacting"""
    context_window: int = 128000  # 128k tokens
    compact_threshold: float = 0.92  # 92%
    preserve_recent_messages: int = 10  # Keep last 10 messages
    compression_ratio: float = 0.5  # Compress to 50% of original


class AutoCompactCore:
    """Core functionality for automatic history compaction"""
    
    def __init__(self, config: Optional[CompactConfig] = None):
        self.config = config or CompactConfig()
        self.token_cache: Dict[str, int] = {}
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text using rough estimation.
        Using ~4 characters per token for English text with adjustments.
        """
        # Cache token counts to avoid recalculation
        cache_key = self._hash_string(text)
        if cache_key in self.token_cache:
            return self.token_cache[cache_key]
        
        # Rough estimation: 4 chars per token, with adjustments for code/structured content
        token_count = len(text) // 4
        
        # Adjust for code blocks (typically more dense)
        code_block_matches = re.findall(r'```[\s\S]*?```', text)
        if code_block_matches:
            token_count += len(code_block_matches) * 10  # Add overhead for code blocks
        
        # Adjust for JSON/structured data (more dense)
        if '{' in text and '}' in text:
            token_count = int(token_count * 1.2)
        
        self.token_cache[cache_key] = token_count
        return token_count
    
    def calculate_history_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Calculate total token count for message history"""
        total = 0
        for message in messages:
            content_tokens = self.estimate_tokens(message.get('content', ''))
            role_tokens = self.estimate_tokens(message.get('role', ''))
            total += content_tokens + role_tokens + 3  # +3 for message structure overhead
        return total
    
    def needs_compacting(self, messages: List[Dict[str, Any]]) -> bool:
        """Check if history needs compacting"""
        total_tokens = self.calculate_history_tokens(messages)
        threshold = self.config.context_window * self.config.compact_threshold
        return total_tokens > threshold
    
    def _compress_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Compress message content while preserving key information"""
        content = message.get('content', '')
        
        # Preserve system messages and short messages as-is
        if message.get('role') == 'system' or len(content) < 200:
            return message
        
        # Compress code blocks by keeping only essential parts
        def compress_code_block(match):
            lines = match.group(0).split('\n')
            if len(lines) <= 10:
                return match.group(0)  # Keep short code blocks
            
            # Keep first 3 and last 3 lines, summarize middle
            start = '\n'.join(lines[:3])
            end = '\n'.join(lines[-3:])
            omitted_count = len(lines) - 6
            return f"{start}\n// ... {omitted_count} lines omitted ...\n{end}"
        
        content = re.sub(r'```[\s\S]*?```', compress_code_block, content)
        
        # Compress long paragraphs
        def compress_paragraph(match):
            paragraph = match.group(1)
            sentences = [s.strip() for s in re.split(r'[.!?]+', paragraph) if s.strip()]
            if len(sentences) <= 2:
                return match.group(0)
            
            first_sentence = sentences[0] + '.'
            last_sentence = sentences[-1] + '.'
            return f"\n\n{first_sentence} [...] {last_sentence}\n\n"
        
        content = re.sub(r'\n\n([^\n]{200,})\n\n', compress_paragraph, content)
        
        # Remove excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r'[ \t]{2,}', ' ', content)
        
        compressed_message = message.copy()
        compressed_message['content'] = content.strip()
        compressed_message['_compressed'] = True
        return compressed_message
    
    def compact_history(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compact message history by removing and compressing older messages"""
        if not self.needs_compacting(messages):
            return messages
        
        recent_messages = messages[-self.config.preserve_recent_messages:]
        older_messages = messages[:-self.config.preserve_recent_messages]
        
        # Calculate how many older messages to keep
        target_older_count = int(len(older_messages) * self.config.compression_ratio)
        
        # Keep system messages and important messages
        system_messages = [m for m in older_messages if m.get('role') == 'system']
        non_system_messages = [m for m in older_messages if m.get('role') != 'system']
        
        # Sample non-system messages evenly
        if target_older_count > 0 and non_system_messages:
            step = max(1, len(non_system_messages) // target_older_count)
            sampled_messages = [non_system_messages[i] for i in range(0, len(non_system_messages), step)]
        else:
            sampled_messages = []
        
        # Compress the sampled messages
        compressed_older = [self._compress_message(m) for m in system_messages + sampled_messages]
        
        # Add a summary message about the compression
        compression_summary = {
            'role': 'system',
            'content': f'[AUTO_COMPACT] Compressed {len(older_messages) - len(compressed_older)} messages to save context space. Recent {self.config.preserve_recent_messages} messages preserved.',
            '_compaction_marker': True
        }
        
        return compressed_older + [compression_summary] + recent_messages
    
    def get_context_stats(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get current context usage statistics"""
        total_tokens = self.calculate_history_tokens(messages)
        usage_percentage = total_tokens / self.config.context_window
        
        return {
            'total_tokens': total_tokens,
            'usage_percentage': usage_percentage,
            'needs_compacting': self.needs_compacting(messages),
            'remaining_tokens': self.config.context_window - total_tokens
        }
    
    def _hash_string(self, text: str) -> str:
        """Simple string hash for caching"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def clear_cache(self) -> None:
        """Clear token cache (useful for memory management)"""
        self.token_cache.clear()
    
    def update_config(self, **kwargs) -> None:
        """Update configuration"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)