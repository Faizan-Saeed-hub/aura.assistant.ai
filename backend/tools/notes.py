from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.database import get_connection

def add_note(title: str, content: str = "", due_date: str = "") -> str:
    """Create a new personal note or reminder."""
    now = datetime.now().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notes (title, content, status, due_date, created_at) VALUES (?, ?, 'pending', ?, ?)",
        (title.strip(), content.strip(), due_date.strip(), now)
    )
    note_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return f"Saved note #{note_id}: '{title}'" + (f" (Due: {due_date})" if due_date else "")

def list_notes(status: str = "pending") -> str:
    """List user notes and reminders by status ('pending', 'completed', or 'all')."""
    conn = get_connection()
    if status == "all":
        rows = conn.execute("SELECT * FROM notes ORDER BY id DESC").fetchall()
    else:
        rows = conn.execute("SELECT * FROM notes WHERE status = ? ORDER BY id DESC", (status,)).fetchall()
    conn.close()
    
    if not rows:
        return f"No {status} notes or reminders found."
    
    output = [f"**Your {status.capitalize()} Notes & Reminders:**"]
    for r in rows:
        due = f" [Due: {r['due_date']}]" if r["due_date"] else ""
        body = f" - {r['content']}" if r["content"] else ""
        mark = "✓" if r["status"] == "completed" else "○"
        output.append(f"{mark} #{r['id']}: **{r['title']}**{due}{body}")
    return "\n".join(output)

def complete_note(note_id: int) -> str:
    """Mark a note or reminder as completed by its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notes SET status = 'completed' WHERE id = ?", (note_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    if affected > 0:
        return f"Note #{note_id} marked as completed."
    return f"Note #{note_id} was not found."

def delete_note(note_id: int) -> str:
    """Delete a note or reminder by its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    if affected > 0:
        return f"Note #{note_id} deleted."
    return f"Note #{note_id} not found."
