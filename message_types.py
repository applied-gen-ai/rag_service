"""
Message type definitions for WebSocket communication
"""
import json
from typing import Dict, Any, List


def status_message(message: str) -> str:
    """Create a status update message"""
    return json.dumps({
        "type": "status",
        "message": message
    })


def token_message(content: str) -> str:
    """Create a token message for streaming"""
    return json.dumps({
        "type": "token",
        "content": content
    })


def error_message(message: str, details: str = None) -> str:
    """Create an error message"""
    msg = {
        "type": "error",
        "message": message
    }
    if details:
        msg["details"] = details
    return json.dumps(msg)


def done_message(message: str = "Complete") -> str:
    """Create a completion message"""
    return json.dumps({
        "type": "done",
        "message": message
    })


def citation_message(sources: List[Dict[str, Any]]) -> str:
    """
    Create a citation message showing sources used
    
    Args:
        sources: List of source dictionaries with score, text, metadata
        
    Returns:
        JSON string with citation information
    """
    return json.dumps({
        "type": "citation",
        "sources": sources
    })