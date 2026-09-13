from typing import List, Dict, Any
from backend.database import get_session_messages, add_message, get_connection
from backend.config import config

class ConversationManager:
    """Manages short-term conversation context for an active session."""
    
    @staticmethod
    def get_context(session_id: str, max_messages: int = None) -> List[Dict[str, Any]]:
        """Retrieve recent conversation history formatted for the LLM."""
        limit = max_messages or config.MAX_SHORT_TERM_MESSAGES
        messages = get_session_messages(session_id, limit=limit)
        
        formatted = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            formatted.append({
                "role": role,
                "content": content
            })
        return formatted

    @staticmethod
    def append_message(session_id: str, role: str, content: str, tool_calls=None, citations=None) -> int:
        return add_message(session_id, role, content, tool_calls=tool_calls, citations=citations)

    @staticmethod
    def clear_history(session_id: str):
        conn = get_connection()
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()

conversation_manager = ConversationManager()
