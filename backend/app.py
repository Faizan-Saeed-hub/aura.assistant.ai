import os
import json
import uuid
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import Config, config, UPLOADS_DIR, AVATARS_DIR, BASE_DIR
from backend.database import (
    init_db, create_session, get_all_sessions, get_session, delete_session,
    get_session_messages, get_setting, set_setting, get_connection,
    get_active_user, create_user_account, update_user_profile,
    DEFAULT_MALE_AVATAR, DEFAULT_FEMALE_AVATAR
)
from backend.memory.long_term import long_term_memory
from backend.rag.parser import document_parser
from backend.rag.chunker import text_chunker
from backend.rag.vector_store import vector_store
from backend.agent.orchestrator import agent_orchestrator
from backend.tools.notes import add_note, list_notes, complete_note, delete_note
from backend.llm.client import llm_client

# Initialize Database
init_db()

app = FastAPI(title=config.PROJECT_NAME, version=config.VERSION)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = BASE_DIR / "frontend"

# Request Schemas
class ChatRequest(BaseModel):
    session_id: str
    message: str
    provider: Optional[str] = None
    model: Optional[str] = None

class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Chat"

class MemoryCreateRequest(BaseModel):
    category: str
    content: str
    importance: Optional[int] = 3

class NoteCreateRequest(BaseModel):
    title: str
    content: Optional[str] = ""
    due_date: Optional[str] = ""

class EmailGenerateRequest(BaseModel):
    purpose: str
    recipient_name: Optional[str] = ""
    recipient_company: Optional[str] = ""
    tone: Optional[str] = "Professional"
    key_points: str
    sender_name: Optional[str] = None
    sender_role: Optional[str] = None

class SettingsUpdateRequest(BaseModel):
    active_provider: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    openrouter_model: Optional[str] = None
    gemini_model: Optional[str] = None
    groq_model: Optional[str] = None
    openai_model: Optional[str] = None

# --- Chat & Session Endpoints ---

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Verify session or create if missing
    sess = get_session(req.session_id)
    if not sess:
        create_session(req.session_id, title=req.message[:30] + ("..." if len(req.message) > 30 else ""))
    
    try:
        result = await agent_orchestrator.process_message(
            session_id=req.session_id,
            user_message=req.message,
            provider=req.provider,
            model=req.model
        )
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "text": f"⚠️ Error processing message: {str(e)}",
            "tool_calls": [],
            "citations": []
        }

@app.get("/api/sessions")
def list_sessions():
    return get_all_sessions()

@app.post("/api/sessions")
def new_session(req: CreateSessionRequest):
    sid = str(uuid.uuid4())[:8]
    return create_session(sid, title=req.title or "New Chat")

@app.delete("/api/sessions/{session_id}")
def remove_session(session_id: str):
    delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}

@app.get("/api/sessions/{session_id}/messages")
def get_messages(session_id: str):
    return get_session_messages(session_id)

# --- Long-Term Memory Endpoints ---

@app.get("/api/memories")
def get_memories():
    return long_term_memory.get_all()

@app.post("/api/memories")
def create_memory(req: MemoryCreateRequest):
    mem_id = long_term_memory.add(category=req.category, content=req.content, importance=req.importance, source="manual")
    return {"id": mem_id, "status": "created"}

@app.delete("/api/memories/{memory_id}")
def delete_memory_endpoint(memory_id: int):
    success = long_term_memory.delete(memory_id)
    return {"status": "deleted" if success else "not_found"}

# --- RAG Knowledge Base Endpoints ---

@app.post("/api/rag/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    doc_id = str(uuid.uuid4())[:8]
    clean_name = Path(file.filename).name
    save_path = UPLOADS_DIR / f"{doc_id}_{clean_name}"

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Parse document
        parsed_pages = document_parser.parse_file(str(save_path))
        # Split into chunks
        chunks = text_chunker.chunk_document(doc_id, parsed_pages)
        
        # Add to vector store
        vector_store.add_chunks(chunks)

        # Store in sqlite documents table
        from datetime import datetime
        now = datetime.now().isoformat()
        conn = get_connection()
        conn.execute(
            "INSERT INTO documents (id, filename, file_type, chunk_count, file_path, uploaded_at) VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, clean_name, save_path.suffix.lower(), len(chunks), str(save_path), now)
        )
        conn.commit()
        conn.close()

        return {
            "status": "indexed",
            "doc_id": doc_id,
            "filename": clean_name,
            "chunk_count": len(chunks)
        }
    except Exception as e:
        if save_path.exists():
            save_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

@app.get("/api/rag/documents")
def list_documents():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.delete("/api/rag/documents/{doc_id}")
def delete_document(doc_id: str):
    conn = get_connection()
    row = conn.execute("SELECT file_path FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if row:
        fpath = Path(row["file_path"])
        if fpath.exists():
            try:
                fpath.unlink()
            except Exception:
                pass
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()
    
    # Remove from vector store
    vector_store.delete_document(doc_id)
    return {"status": "deleted", "doc_id": doc_id}

# --- Notes & Reminders Endpoints ---

@app.get("/api/notes")
def get_notes(status: str = "all"):
    conn = get_connection()
    if status == "all":
        rows = conn.execute("SELECT * FROM notes ORDER BY id DESC").fetchall()
    else:
        rows = conn.execute("SELECT * FROM notes WHERE status = ? ORDER BY id DESC", (status,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/notes")
def create_note_endpoint(req: NoteCreateRequest):
    res = add_note(title=req.title, content=req.content, due_date=req.due_date)
    return {"message": res}

@app.put("/api/notes/{note_id}/complete")
def complete_note_endpoint(note_id: int):
    res = complete_note(note_id)
    return {"message": res}

@app.delete("/api/notes/{note_id}")
def delete_note_endpoint(note_id: int):
    res = delete_note(note_id)
    return {"message": res}

# --- Email Customization & Composition Studio ---

@app.post("/api/email/generate")
async def generate_email(req: EmailGenerateRequest):
    """Generate high-converting, professional email based on user tone, purpose, and key points."""
    active_user = get_active_user()
    sender_name = req.sender_name or active_user.get("name", "Muhammad Faizan")
    sender_role = req.sender_role or active_user.get("role", "Professional")
    
    prompt = f"""You are an elite communications specialist. Compose a tailored, top-tier email with these specifications:
- Purpose / Goal: {req.purpose}
- Recipient Name: {req.recipient_name or 'Hiring Team / Contact'}
- Recipient Organization / Company: {req.recipient_company or 'Organization'}
- Tone: {req.tone or 'Professional'}
- Key Points / Topics to cover: {req.key_points}
- Sender: {sender_name} ({sender_role})

Output ONLY valid JSON in this exact structure:
{{
  "subject": "Clear, engaging subject line here",
  "body": "Full body with salutation, structured paragraphs, bullet points if helpful, clear call to action, and professional sign-off by {sender_name}"
}}"""

    try:
        res = await llm_client.generate_response(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are a master business email composer. Output raw valid JSON with 'subject' and 'body' keys.",
            tools_enabled=False
        )
        text = res.get("text", "").strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())
        return {
            "status": "success",
            "subject": data.get("subject", f"Regarding {req.purpose}"),
            "body": data.get("body", text)
        }
    except Exception as e:
        # High quality resilient template fallback
        recipient = req.recipient_name or "Colleague"
        subj = f"{req.purpose}: Discussion with {sender_name}"
        body = (
            f"Dear {recipient},\n\n"
            f"I hope this message finds you well.\n\n"
            f"I am reaching out regarding {req.purpose.lower()}.\n\n"
            f"{req.key_points}\n\n"
            f"I look forward to your thoughts and would welcome the opportunity to connect at your earliest convenience.\n\n"
            f"Best regards,\n"
            f"{sender_name}\n"
            f"{sender_role}"
        )
        return {
            "status": "success",
            "subject": subj,
            "body": body
        }

# --- Settings Endpoints ---

@app.get("/api/settings")
def get_settings():
    prov = get_setting("ACTIVE_PROVIDER", config.DEFAULT_PROVIDER)
    openrouter_key = get_setting("OPENROUTER_API_KEY", config.OPENROUTER_API_KEY)
    gemini_key = get_setting("GEMINI_API_KEY", config.GEMINI_API_KEY)
    groq_key = get_setting("GROQ_API_KEY", config.GROQ_API_KEY)
    openai_key = get_setting("OPENAI_API_KEY", config.OPENAI_API_KEY)

    def mask(k: str) -> str:
        if not k or len(k) < 8:
            return ""
        return k[:4] + "••••••••" + k[-4:]

    return {
        "active_provider": prov,
        "openrouter_configured": bool(openrouter_key),
        "gemini_configured": bool(gemini_key),
        "groq_configured": bool(groq_key),
        "openai_configured": bool(openai_key),
        "openrouter_masked": mask(openrouter_key),
        "gemini_masked": mask(gemini_key),
        "groq_masked": mask(groq_key),
        "openai_masked": mask(openai_key),
        "openrouter_model": get_setting("OPENROUTER_MODEL", config.DEFAULT_OPENROUTER_MODEL),
        "gemini_model": get_setting("GEMINI_MODEL", config.DEFAULT_GEMINI_MODEL),
        "groq_model": get_setting("GROQ_MODEL", config.DEFAULT_GROQ_MODEL),
        "openai_model": get_setting("OPENAI_MODEL", config.DEFAULT_OPENAI_MODEL),
    }

def update_env_file(updates: Dict[str, str]):
    """Sync runtime settings directly to .env file on disk."""
    env_path = BASE_DIR / ".env"
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    updated_keys = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        if "=" in stripped:
            k, _ = stripped.split("=", 1)
            k = k.strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}\n")
                updated_keys.add(k)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    for k, v in updates.items():
        if k not in updated_keys:
            new_lines.append(f"{k}={v}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

@app.post("/api/settings")
def update_settings(req: SettingsUpdateRequest):
    env_updates = {}
    if req.active_provider:
        set_setting("ACTIVE_PROVIDER", req.active_provider)
        env_updates["DEFAULT_PROVIDER"] = req.active_provider
    if req.openrouter_api_key is not None and req.openrouter_api_key.strip():
        val = req.openrouter_api_key.strip()
        set_setting("OPENROUTER_API_KEY", val)
        env_updates["OPENROUTER_API_KEY"] = val
        os.environ["OPENROUTER_API_KEY"] = val
    if req.gemini_api_key is not None and req.gemini_api_key.strip():
        val = req.gemini_api_key.strip()
        set_setting("GEMINI_API_KEY", val)
        env_updates["GEMINI_API_KEY"] = val
        os.environ["GEMINI_API_KEY"] = val
    if req.groq_api_key is not None and req.groq_api_key.strip():
        val = req.groq_api_key.strip()
        set_setting("GROQ_API_KEY", val)
        env_updates["GROQ_API_KEY"] = val
        os.environ["GROQ_API_KEY"] = val
    if req.openai_api_key is not None and req.openai_api_key.strip():
        val = req.openai_api_key.strip()
        set_setting("OPENAI_API_KEY", val)
        env_updates["OPENAI_API_KEY"] = val
        os.environ["OPENAI_API_KEY"] = val
    if req.openrouter_model:
        set_setting("OPENROUTER_MODEL", req.openrouter_model)
        env_updates["DEFAULT_OPENROUTER_MODEL"] = req.openrouter_model
    if req.gemini_model:
        set_setting("GEMINI_MODEL", req.gemini_model)
        env_updates["DEFAULT_GEMINI_MODEL"] = req.gemini_model
    if req.groq_model:
        set_setting("GROQ_MODEL", req.groq_model)
        env_updates["DEFAULT_GROQ_MODEL"] = req.groq_model
    if req.openai_model:
        set_setting("OPENAI_MODEL", req.openai_model)
        env_updates["DEFAULT_OPENAI_MODEL"] = req.openai_model

    if env_updates:
        try:
            update_env_file(env_updates)
        except Exception as e:
            print(f"[*] Could not write to .env: {e}")

    return {"status": "saved"}

# --- User Profile & Authentication Endpoints ---

class UserRegisterRequest(BaseModel):
    name: str
    email: str
    password: Optional[str] = "secret123"
    gender: Optional[str] = "male"
    role: Optional[str] = "Personal AI User"
    bio: Optional[str] = ""
    avatar_url: Optional[str] = None

class UserProfileUpdateRequest(BaseModel):
    name: str
    email: str
    gender: Optional[str] = "male"
    role: Optional[str] = "Personal AI User"
    bio: Optional[str] = ""
    avatar_url: Optional[str] = None

@app.get("/api/user/profile")
def get_profile():
    return get_active_user()

@app.post("/api/user/avatar")
async def upload_user_avatar(file: UploadFile = File(...)):
    """Upload custom profile picture (DP) and save locally."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    ext = Path(file.filename).suffix.lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"]:
        ext = ".png"

    avatar_filename = f"avatar_{uuid.uuid4().hex[:12]}{ext}"
    avatar_path = AVATARS_DIR / avatar_filename

    with open(avatar_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    avatar_url = f"/avatars/{avatar_filename}"
    return {"status": "success", "avatar_url": avatar_url}

@app.post("/api/auth/register")
def register_user(req: UserRegisterRequest):
    if not req.name.strip() or not req.email.strip():
        raise HTTPException(status_code=400, detail="Name and email are required")
    user = create_user_account(
        name=req.name.strip(),
        email=req.email.strip().lower(),
        password=req.password or "secret123",
        gender=req.gender or "male",
        role=req.role.strip() if req.role else "Personal AI User",
        bio=req.bio.strip() if req.bio else "",
        avatar_url=req.avatar_url
    )
    return {"status": "success", "user": user}

@app.put("/api/user/profile")
def update_profile(req: UserProfileUpdateRequest):
    import sqlite3
    curr = get_active_user()
    user_id = curr.get("id", 1)
    try:
        user = update_user_profile(
            user_id=user_id,
            name=req.name.strip(),
            email=req.email.strip().lower(),
            gender=req.gender or "male",
            role=req.role.strip() if req.role else "Personal AI User",
            bio=req.bio.strip() if req.bio else "",
            avatar_url=req.avatar_url
        )
        return {"status": "updated", "user": user}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="This email address is already registered to another user.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Static Frontend & Media Serving ---

app.mount("/avatars", StaticFiles(directory=str(AVATARS_DIR)), name="avatars")
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")
