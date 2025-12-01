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
    
    def _extract_text_from_content(self, content: Any) -> str:
        """
        Extract text from content, handling both string and OpenAI list formats.
        
        OpenAI format can be:
        - Simple string: "Hello world"
        - List format: [{"type": "text", "text": "Hello"}, {"type": "image_url", "image_url": {...}}]
        """
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            # Extract text from OpenAI list format
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get('type') == 'text' and 'text' in item:
                        text_parts.append(item['text'])
                    elif item.get('type') == 'image_url':
                        # Add placeholder for image tokens (images typically use ~85 tokens)
                        text_parts.append('[IMAGE_PLACEHOLDER_85_TOKENS]')
                    else:
                        # Handle other content types
                        text_parts.append(str(item))
                else:
                    text_parts.append(str(item))
            return ' '.join(text_parts)
        else:
            # Fallback for other types
            return str(content) if content is not None else ''

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text using rough estimation.
        Using ~4 characters per token for English text with adjustments.
        """
        # Cache token counts to avoid recalculation
        cache_key = self._hash_string(text)
        if cache_key in self.token_cache:
            return self.token_cache[cache_key]
        
        # Handle image placeholders
        if '[IMAGE_PLACEHOLDER_85_TOKENS]' in text:
            image_count = text.count('[IMAGE_PLACEHOLDER_85_TOKENS]')
            text = text.replace('[IMAGE_PLACEHOLDER_85_TOKENS]', '')
            image_tokens = image_count * 85
        else:
            image_tokens = 0
        
        # Rough estimation: 4 chars per token, with adjustments for code/structured content
        token_count = len(text) // 4
        
        # Adjust for code blocks (typically more dense)
        code_block_matches = re.findall(r'```[\s\S]*?```', text)
        if code_block_matches:
            token_count += len(code_block_matches) * 10  # Add overhead for code blocks
        
        # Adjust for JSON/structured data (more dense)
        if '{' in text and '}' in text:
            token_count = int(token_count * 1.2)
        
        # Add image tokens
        token_count += image_tokens
        
        self.token_cache[cache_key] = token_count
        return token_count
    
    def calculate_history_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Calculate total token count for message history"""
        total = 0
        for message in messages:
            # Extract text from content (handles both string and list formats)
            content = message.get('content', '')
            content_text = self._extract_text_from_content(content)
            content_tokens = self.estimate_tokens(content_text)
            
            # Role is always a string
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
        
        # Handle different content formats
        if isinstance(content, list):
            # For OpenAI list format, we need to compress text parts only
            return self._compress_list_content_message(message)
        
        # Handle string content
        content_text = self._extract_text_from_content(content)
        
        # Preserve system messages and short messages as-is
        if message.get('role') == 'system' or len(content_text) < 200:
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
    
    def _compress_list_content_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Compress message with list-format content (OpenAI format)"""
        content_list = message.get('content', [])
        if not isinstance(content_list, list):
            return message
        
        compressed_content = []
        for item in content_list:
            if isinstance(item, dict):
                if item.get('type') == 'text' and 'text' in item:
                    # Compress text content
                    original_text = item['text']
                    if len(original_text) < 200:
                        compressed_content.append(item)  # Keep short text as-is
                    else:
                        # Apply text compression
                        compressed_text = self._compress_text_content(original_text)
                        compressed_item = item.copy()
                        compressed_item['text'] = compressed_text
                        compressed_content.append(compressed_item)
                else:
                    # Keep non-text items (images, etc.) as-is
                    compressed_content.append(item)
            else:
                compressed_content.append(item)
        
        compressed_message = message.copy()
        compressed_message['content'] = compressed_content
        compressed_message['_compressed'] = True
        return compressed_message
    
    def _compress_text_content(self, text: str) -> str:
        """Compress text content using the same logic as string compression"""
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
        
        text = re.sub(r'```[\s\S]*?```', compress_code_block, text)
        
        # Compress long paragraphs
        def compress_paragraph(match):
            paragraph = match.group(1)
            sentences = [s.strip() for s in re.split(r'[.!?]+', paragraph) if s.strip()]
            if len(sentences) <= 2:
                return match.group(0)
            
            first_sentence = sentences[0] + '.'
            last_sentence = sentences[-1] + '.'
            return f"\n\n{first_sentence} [...] {last_sentence}\n\n"
        
        text = re.sub(r'\n\n([^\n]{200,})\n\n', compress_paragraph, text)
        
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]{2,}', ' ', text)
        
        return text.strip()
    
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
            'role': 'user',
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