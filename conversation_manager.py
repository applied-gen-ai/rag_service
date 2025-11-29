"""
Conversation history management for multi-turn chat
"""
import logging
from typing import List, Dict, Any
from collections import deque

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation history for a single session"""
    
    def __init__(self, max_turns: int = 5):
        """
        Initialize conversation manager
        
        Args:
            max_turns: Maximum number of conversation turns to keep
        """
        self.max_turns = max_turns
        self.history = deque(maxlen=max_turns * 2)  # *2 for user+assistant pairs
        logger.info(f"ConversationManager initialized (max_turns: {max_turns})")
    
    def add_user_message(self, message: str):
        """Add user message to history"""
        self.history.append({
            "role": "user",
            "content": message
        })
        logger.debug(f"Added user message: {message[:50]}...")
    
    def add_assistant_message(self, message: str):
        """Add assistant message to history"""
        self.history.append({
            "role": "assistant",
            "content": message
        })
        logger.debug(f"Added assistant message: {message[:50]}...")
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history as list"""
        return list(self.history)
    
    def get_formatted_history(self) -> str:
        """Get conversation history as formatted string"""
        if not self.history:
            return ""
        
        formatted = []
        for msg in self.history:
            role = "User" if msg["role"] == "user" else "Assistant"
            formatted.append(f"{role}: {msg['content']}")
        
        return "\n".join(formatted)
    
    def clear(self):
        """Clear conversation history"""
        self.history.clear()
        logger.info("Conversation history cleared")
    
    def get_turn_count(self) -> int:
        """Get number of conversation turns"""
        return len(self.history) // 2
    
    def is_empty(self) -> bool:
        """Check if conversation history is empty"""
        return len(self.history) == 0