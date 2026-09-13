import os
import sys
import time
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.database import init_db, create_session, add_message, get_session_messages, delete_session
from backend.memory.long_term import long_term_memory
from backend.tools.calculator import calculate
from backend.tools.weather import get_weather
from backend.tools.system_info import get_system_info
from backend.tools.wikipedia import wikipedia_lookup
from backend.tools.notes import add_note, list_notes, complete_note
from backend.tools.registry import execute_tool
from backend.rag.chunker import text_chunker
from backend.rag.vector_store import vector_store

def run_tests():
    print("🚀 Running AI Personal Assistant Subsystem Tests...")
    
    # 1. Database & Session Test
    print("\n[1] Testing Database & Sessions...")
    init_db()
    test_sess_id = f"test_sess_{int(time.time())}"
    sess = create_session(test_sess_id, title="Test Session")
    assert sess["id"] == test_sess_id
    msg_id = add_message(test_sess_id, "user", "Hello Assistant!")
    msgs = get_session_messages(test_sess_id)
    assert len(msgs) == 1
    assert msgs[0]["content"] == "Hello Assistant!"
    delete_session(test_sess_id)
    print("  ✓ Database & Chat History test passed.")

    # 2. Long-Term Memory Test
    print("\n[2] Testing Long-Term Memory...")
    mem_id = long_term_memory.add("preference", "User prefers Python over JavaScript", importance=5)
    all_mems = long_term_memory.get_all()
    assert any(m["content"] == "User prefers Python over JavaScript" for m in all_mems)
    prompt_str = long_term_memory.format_for_prompt()
    assert "User prefers Python over JavaScript" in prompt_str
    print("  ✓ Long-Term Memory test passed.")

    # 3. Tools & APIs Test
    print("\n[3] Testing Agentic Tools...")
    
    # Calculator
    calc_res = calculate("25 * 4 + 10")
    assert "110" in calc_res
    print(f"  ✓ Calculator: {calc_res}")

    # System Info
    sys_res = get_system_info()
    assert "Current Time:" in sys_res
    print("  ✓ System Info verified.")

    # Notes
    note_msg = add_note("Buy groceries", due_date="Tonight")
    assert "Saved note" in note_msg
    notes_list = list_notes("pending")
    assert "Buy groceries" in notes_list
    print("  ✓ Notes & Reminders verified.")

    # Weather (Live Open-Meteo free API)
    print("  Testing Weather API (Open-Meteo)...")
    try:
        w_res = get_weather("London")
        print(f"  ✓ Weather Result: {w_res.splitlines()[0]}")
    except Exception as e:
        print(f"  ⚠️ Weather network test note: {e}")

    # Wikipedia (Live Wikipedia API)
    print("  Testing Wikipedia API...")
    try:
        wiki_res = wikipedia_lookup("Python (programming language)")
        print(f"  ✓ Wikipedia Result: {wiki_res[:60]}...")
    except Exception as e:
        print(f"  ⚠️ Wikipedia network test note: {e}")

    # 4. RAG Pipeline Test
    print("\n[4] Testing RAG (Chunking + Vector Store)...")
    sample_text = """Antigravity is an advanced software engineering system.
    It provides intelligent pair programming, browser automation, and deep terminal access.
    Artificial Intelligence personal assistants can automate daily tasks like scheduling, document QA, and research.
    RAG allows models to ground their answers in private documents without hallucination."""

    chunks = text_chunker.split_text(sample_text)
    assert len(chunks) > 0
    formatted_chunks = [{
        "id": f"test_doc_{i}",
        "doc_id": "test_doc",
        "chunk_index": i,
        "filename": "test_doc.txt",
        "page": 1,
        "text": c
    } for i, c in enumerate(chunks)]

    vector_store.add_chunks(formatted_chunks)
    search_res = vector_store.search("How does RAG help AI assistants?", top_k=2)
    assert len(search_res) > 0
    print(f"  ✓ RAG Search match score: {search_res[0]['score']}")
    print(f"  ✓ Top chunk snippet: {search_res[0]['text'][:70]}...")

    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
