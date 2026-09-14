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
    get_active_user, create_user_account, update_user_profile, authenticate_user,
    get_all_users_for_admin, delete_user_by_admin,
    DEFAULT_MALE_AVATAR, DEFAULT_FEMALE_AVATAR
)
from backend.memory.long_term import long_term_memory
from backend.rag.parser import document_parser
from backend.rag.chunker import text_chunker
from backend.rag.vector_store import vector_store
from backend.agent.orchestrator import agent_orchestrator
from backend.tools.notes import add_note, list_notes, complete_note, delete_note
from backend.tools.image_studio import generate_ai_image, retouch_image_file, replace_image_background
from backend.auth.supabase_client import supabase_auth
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
    session_id: Optional[str] = None
    message: str
    provider: Optional[str] = None
    model: Optional[str] = None
    user_id: Optional[int] = None

class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Chat"
    user_id: Optional[int] = None

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
    openrouter_model: Optional[str] = None
    gemini_model: Optional[str] = None
    groq_model: Optional[str] = None

class AuthSignupRequest(BaseModel):
    email: str
    password: str
    name: str
    role: Optional[str] = "Creator"
    gender: Optional[str] = "male"
    avatar_url: Optional[str] = None

class AuthLoginRequest(BaseModel):
    email: str
    password: str

class ChangeBgRequest(BaseModel):
    image_data: str
    new_bg_color: Optional[str] = "#ffffff"
    target_bg_color: Optional[str] = None
    tolerance: Optional[int] = 35
    feather: Optional[int] = 3
    use_ai: Optional[bool] = False

# --- Chat & Session Endpoints ---


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Model Access Control: Guests can ONLY use default Groq; Gemini & OpenRouter require login
    active_settings = get_settings()
    target_provider = (req.provider or active_settings.get("active_provider") or "groq").lower()
    is_authenticated = bool(req.user_id and req.user_id > 0)

    if not is_authenticated and target_provider in ["gemini", "openrouter", "ollama"]:
        return {
            "text": "🔒 **Account Required to Unlock Google Gemini & OpenRouter**\n\nYou are currently chatting in Free Guest Mode with **Groq**. To unlock Gemini 2.5 Flash, OpenRouter, and persistent cross-device chat history, please **sign in or create a free account** in the top right!",
            "auth_required": True,
            "tool_calls": [],
            "citations": []
        }

    # Verify session or create if missing
    import time
    session_id = req.session_id or f"sess_{int(time.time()*1000)}"
    sess = get_session(session_id)
    if not sess:
        create_session(session_id, title=req.message[:30] + ("..." if len(req.message) > 30 else ""), user_id=req.user_id)
    
    try:
        result = await agent_orchestrator.process_message(
            session_id=session_id,
            user_message=req.message,
            provider=target_provider,
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
def list_sessions(user_id: Optional[int] = None):
    return get_all_sessions(user_id=user_id)

@app.post("/api/sessions")
def new_session(req: CreateSessionRequest):
    sid = str(uuid.uuid4())[:8]
    return create_session(sid, title=req.title or "New Chat", user_id=req.user_id)

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

# --- Image Studio & Retouching Endpoints ---

class ImageGenRequest(BaseModel):
    prompt: str
    width: Optional[int] = 1024
    height: Optional[int] = 1024

@app.post("/api/image/generate")
async def api_generate_image(req: ImageGenRequest):
    """Generate high-resolution AI art or concepts."""
    return generate_ai_image(req.prompt, width=req.width or 1024, height=req.height or 1024)

@app.post("/api/image/retouch")
async def api_retouch_image(
    file: UploadFile = File(...),
    preset: str = Form("custom"),
    glow: int = Form(0),
    dark_circles: int = Form(0),
    smooth: int = Form(0),
    warmth: int = Form(0),
    crop_aspect: Optional[str] = Form(None),
    bw: bool = Form(False)
):
    """Upload photo and apply non-destructive face glow, dark circles lift, skin softening, and aspect crop."""
    try:
        from PIL import Image
        import io
        contents = await file.read()
        pil_img = Image.open(io.BytesIO(contents))
        
        # Save original copy
        orig_filename = f"orig_{uuid.uuid4().hex[:8]}_{file.filename}"
        orig_path = UPLOADS_DIR / orig_filename
        with open(orig_path, "wb") as f:
            f.write(contents)
            
        res = retouch_image_file(
            pil_img,
            preset=preset,
            glow=glow,
            dark_circles=dark_circles,
            smooth=smooth,
            warmth=warmth,
            crop_aspect=crop_aspect,
            bw=bw
        )
        if res.get("success"):
            res["original_url"] = f"/data/uploads/{orig_filename}"
            res["download_url"] = f"/api/image/download/{res['filename']}"
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/image/download/{filename}")
def download_retouched_image(filename: str):
    """Serve image with attachment headers so browser initiates clean download."""
    clean_name = os.path.basename(filename)
    file_path = UPLOADS_DIR / clean_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Requested image file was not found on server")
    return FileResponse(
        str(file_path),
        media_type="image/jpeg",
        filename=clean_name,
        headers={"Content-Disposition": f'attachment; filename="{clean_name}"'}
    )

# --- Settings & Model Provider Endpoints ---

@app.get("/api/settings")
def get_settings():
    prov = get_setting("ACTIVE_PROVIDER", config.DEFAULT_PROVIDER)
    openrouter_key = get_setting("OPENROUTER_API_KEY", config.OPENROUTER_API_KEY)
    gemini_key = get_setting("GEMINI_API_KEY", config.GEMINI_API_KEY)
    groq_key = get_setting("GROQ_API_KEY", config.GROQ_API_KEY)

    def mask(k: str) -> str:
        if not k or len(k) < 8:
            return ""
        return k[:4] + "••••••••" + k[-4:]

    return {
        "active_provider": prov,
        "default_guest_provider": "groq",
        "groq_configured": bool(groq_key),
        "gemini_configured": bool(gemini_key),
        "openrouter_configured": bool(openrouter_key),
        "groq_masked": mask(groq_key),
        "gemini_masked": mask(gemini_key),
        "openrouter_masked": mask(openrouter_key),
        "groq_model": get_setting("GROQ_MODEL", config.DEFAULT_GROQ_MODEL),
        "gemini_model": get_setting("GEMINI_MODEL", config.DEFAULT_GEMINI_MODEL),
        "openrouter_model": get_setting("OPENROUTER_MODEL", config.DEFAULT_OPENROUTER_MODEL),
        "supabase_configured": supabase_auth.is_configured(),
        "byok_instructions": {
            "gemini": {
                "name": "Google Gemini 2.5 Flash",
                "free_tier": True,
                "url": "https://aistudio.google.com/app/apikey",
                "instructions": "1. Visit https://aistudio.google.com/app/apikey\n2. Sign in with Google\n3. Click 'Create API key'\n4. Paste the key below to unlock Gemini 2.5 Flash!"
            },
            "groq": {
                "name": "Groq Cloud (Default Free Public Engine)",
                "free_tier": True,
                "url": "https://console.groq.com/keys",
                "instructions": "Groq is provided free by default! Anyone can use it without logging in."
            },
            "openrouter": {
                "name": "OpenRouter",
                "free_tier": True,
                "url": "https://openrouter.ai/keys",
                "instructions": "Get free API keys at https://openrouter.ai/keys."
            }
        }
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
    if req.groq_api_key is not None and req.groq_api_key.strip():
        val = req.groq_api_key.strip()
        set_setting("GROQ_API_KEY", val)
        env_updates["GROQ_API_KEY"] = val
        os.environ["GROQ_API_KEY"] = val
    if req.gemini_api_key is not None and req.gemini_api_key.strip():
        val = req.gemini_api_key.strip()
        set_setting("GEMINI_API_KEY", val)
        env_updates["GEMINI_API_KEY"] = val
        os.environ["GEMINI_API_KEY"] = val
    if req.openrouter_api_key is not None and req.openrouter_api_key.strip():
        val = req.openrouter_api_key.strip()
        set_setting("OPENROUTER_API_KEY", val)
        env_updates["OPENROUTER_API_KEY"] = val
        os.environ["OPENROUTER_API_KEY"] = val
    if req.groq_model:
        set_setting("GROQ_MODEL", req.groq_model)
        env_updates["DEFAULT_GROQ_MODEL"] = req.groq_model
    if req.gemini_model:
        set_setting("GEMINI_MODEL", req.gemini_model)
        env_updates["DEFAULT_GEMINI_MODEL"] = req.gemini_model
    if req.openrouter_model:
        set_setting("OPENROUTER_MODEL", req.openrouter_model)
        env_updates["DEFAULT_OPENROUTER_MODEL"] = req.openrouter_model

    if env_updates:
        try:
            update_env_file(env_updates)
        except Exception as e:
            print(f"[*] Could not write to .env: {e}")

    return {"status": "success", "message": "Settings updated successfully"}



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

@app.post("/api/auth/signup")
async def auth_signup(req: AuthSignupRequest):
    if not req.name.strip() or not req.email.strip() or not req.password:
        raise HTTPException(status_code=400, detail="Name, email, and password are required")
    res = await supabase_auth.signup(
        email=req.email.strip().lower(),
        password=req.password,
        name=req.name.strip(),
        role=req.role or "Creator",
        gender=req.gender or "male",
        avatar_url=req.avatar_url
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Signup failed"))
    return res

@app.post("/api/auth/login")
async def auth_login(req: AuthLoginRequest):
    if not req.email.strip() or not req.password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    res = await supabase_auth.login(email=req.email.strip().lower(), password=req.password)
    if not res.get("success"):
        local_user = authenticate_user(req.email.strip().lower(), req.password)
        if local_user:
            return {"success": True, "mode": "local", "user": local_user}
        raise HTTPException(status_code=401, detail=res.get("error", "Invalid email or password"))
    return res

@app.post("/api/auth/logout")
def auth_logout():
    set_setting("ACTIVE_USER_ID", "")
    return {"success": True, "message": "Logged out successfully"}

@app.get("/api/auth/status")
def auth_status(user_id: Optional[int] = None):
    active_user = None
    if user_id:
        conn = get_connection()
        row = conn.execute("SELECT id, name, email, gender, role, avatar_url, bio, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        if row:
            active_user = dict(row)
    if not active_user:
        active_user = get_active_user()
    
    is_authenticated = bool(active_user and active_user.get("email") not in ["guest@workspace.ai", ""])
    return {
        "authenticated": is_authenticated,
        "user": active_user if is_authenticated else None,
        "allowed_providers": ["groq", "gemini", "openrouter"] if is_authenticated else ["groq"],
        "default_provider": "gemini" if is_authenticated else "groq"
    }

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

# --- Image Studio Background Replacement & Media Endpoints ---

@app.post("/api/studio/change-bg")
def api_change_image_bg(req: ChangeBgRequest):
    res = replace_image_background(
        image_input=req.image_data,
        new_bg_color=req.new_bg_color or "#ffffff",
        target_bg_color=req.target_bg_color,
        tolerance=req.tolerance if req.tolerance is not None else 35,
        feather=req.feather if req.feather is not None else 3,
        use_ai=bool(req.use_ai)
    )
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error", "Background replacement failed"))
    return res

@app.get("/api/image/download/{filename}")
def download_image_file(filename: str):
    file_path = UPLOADS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename)

# --- Static Frontend & Media Serving ---

app.mount("/avatars", StaticFiles(directory=str(AVATARS_DIR)), name="avatars")
app.mount("/data/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="data_uploads")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/manifest.json")
def serve_manifest():
    return FileResponse(FRONTEND_DIR / "manifest.json", media_type="application/manifest+json")

@app.get("/sw.js")
def serve_service_worker():
    return FileResponse(FRONTEND_DIR / "sw.js", media_type="application/javascript")

# --- Super Admin Management Endpoints ---

ADMIN_SUPER_EMAIL = "faizanbarvi786@gmail.com"
ADMIN_SUPER_PASS = "Faizan@786"

class AdminLoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/admin/login")
def api_admin_login(req: AdminLoginRequest):
    email_clean = req.email.strip().lower()
    if email_clean == ADMIN_SUPER_EMAIL.lower() and req.password == ADMIN_SUPER_PASS:
        user = authenticate_user(email_clean, req.password)
        return {
            "success": True,
            "admin_token": "admin_auth_token_faizan_786",
            "user": user or {
                "id": 8,
                "name": "Faizan (Admin)",
                "email": ADMIN_SUPER_EMAIL,
                "role": "admin",
                "gender": "male"
            },
            "message": "Super Admin access authorized"
        }
    raise HTTPException(status_code=401, detail="Invalid admin credentials")

@app.get("/api/admin/users")
def api_admin_get_users(admin_token: Optional[str] = None):
    users = get_all_users_for_admin()
    conn = get_connection()
    total_sessions = conn.execute("SELECT COUNT(*) as count FROM sessions").fetchone()["count"]
    total_messages = conn.execute("SELECT COUNT(*) as count FROM messages").fetchone()["count"]
    total_docs = conn.execute("SELECT COUNT(*) as count FROM documents").fetchone()["count"]
    conn.close()

    active_settings = get_settings()
    return {
        "success": True,
        "users": users,
        "stats": {
            "total_users": len(users),
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "total_documents": total_docs,
            "active_provider": active_settings.get("active_provider", "groq"),
            "active_model": active_settings.get("groq_model", "groq/compound-mini"),
            "supabase_configured": supabase_auth.is_configured(),
            "supabase_url": config.SUPABASE_URL or "Not Configured"
        }
    }

@app.delete("/api/admin/users/{user_id}")
def api_admin_delete_user(user_id: int, admin_token: Optional[str] = None):
    res = delete_user_by_admin(user_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to delete user"))
    return res

@app.get("/admin")
@app.get("/admin/")
def serve_admin():
    admin_file = FRONTEND_DIR / "admin.html"
    if admin_file.exists():
        return FileResponse(admin_file)
    return FileResponse(FRONTEND_DIR / "index.html")

