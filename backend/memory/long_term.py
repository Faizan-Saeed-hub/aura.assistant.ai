import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.database import get_connection

class LongTermMemory:
    """Manages persistent personal memories, facts, preferences, and rules about the user."""
    
    @staticmethod
    def add(category: str, content: str, importance: int = 3, source: str = "chat") -> int:
        now = datetime.now().isoformat()
        conn = get_connection()
        # Avoid exact duplicate content
        existing = conn.execute("SELECT id FROM memories WHERE content = ?", (content.strip(),)).fetchone()
        if existing:
            conn.close()
            return existing["id"]
        
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO memories (category, content, importance, source, created_at) VALUES (?, ?, ?, ?, ?)",
            (category.strip().lower(), content.strip(), importance, source, now)
        )
        mem_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return mem_id

    @staticmethod
    def get_all(limit: int = 100) -> List[Dict[str, Any]]:
        conn = get_connection()
        rows = conn.execute("SELECT * FROM memories ORDER BY importance DESC, id DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def delete(memory_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    @staticmethod
    def search(query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search memories using keyword similarity and recency."""
        terms = [f"%{t.strip()}%" for t in query.lower().split() if len(t.strip()) > 2]
        conn = get_connection()
        if not terms:
            rows = conn.execute("SELECT * FROM memories ORDER BY importance DESC, id DESC LIMIT ?", (limit,)).fetchall()
        else:
            clauses = " OR ".join(["LOWER(content) LIKE ?" for _ in terms])
            query_sql = f"SELECT * FROM memories WHERE {clauses} ORDER BY importance DESC, id DESC LIMIT ?"
            rows = conn.execute(query_sql, (*terms, limit)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def delete_by_query(query: str) -> int:
        """Delete memories matching a search query or keyword."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories WHERE LOWER(content) LIKE ?", (f"%{query.strip().lower()}%",))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted_count

    @staticmethod
    def format_for_prompt(limit: int = 15) -> str:
        """Format persistent user memories as a system prompt block with memory IDs."""
        memories = LongTermMemory.get_all(limit=limit)
        if not memories:
            return ""
        
        lines = ["[Personal Knowledge & User Preferences Memory]"]
        for m in memories:
            cat = m["category"].upper()
            content = m["content"]
            lines.append(f"- (Memory ID: {m['id']}) [{cat}]: {content}")
        return "\n".join(lines)

    @staticmethod
    async def extract_facts_from_turn(user_msg: str, assistant_response: str, llm_generate_fn) -> List[str]:
        """Extracts new durable facts or user preferences from the conversation in English or Roman Urdu."""
        # Comprehensive bilingual triggers for English, Roman Urdu, and Urdu script
        triggers = [
            # English triggers
            "my ", "i am ", "i'm ", "i live ", "i work ", "i prefer ", "i like ", "i love ",
            "i hate ", "i want ", "call me ", "remember that ", "remember this ", "note that ",
            # Roman Urdu triggers
            "mera ", "meri ", "mere ", "main ", "mujhe ", "yaad rakhna ", "yaad rakho ",
            "mera naam ", "meri pasand ", "mera kaam ", "meri company ", "main rehta ",
            # Urdu script triggers
            "میرا", "میری", "میرے", "میں", "مجھے", "یاد رکھنا", "یاد رکھو"
        ]
        lower_msg = user_msg.lower()
        if not any(t in lower_msg for t in triggers):
            return []

        prompt = f"""Analyze the following user statement and extract any clear, enduring facts or preferences about the user.
The user may speak in English or Roman Urdu / Urdu.
Do not extract temporary feelings (like "I am hungry" or "main thak gaya").
Only extract long-term facts (e.g., name, location, occupation, preferences, ongoing projects).

User message: "{user_msg}"

Return a JSON array of strings in concise English, for example:
["User is named Muhammad Faizan", "User lives in Lahore", "User prefers Python over JavaScript"]
If there are no enduring facts, return [].
Provide ONLY raw valid JSON array, no explanation."""

        try:
            res = await llm_generate_fn(prompt, system_instruction="You are a precise fact extraction system. Output JSON only.")
            text = res.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            facts = json.loads(text.strip())
            saved = []
            if isinstance(facts, list):
                for fact in facts:
                    if isinstance(fact, str) and len(fact.strip()) > 3:
                        LongTermMemory.add(category="fact", content=fact.strip(), importance=3, source="auto_extracted")
                        saved.append(fact.strip())
            return saved
        except Exception:
            return []

long_term_memory = LongTermMemory()

