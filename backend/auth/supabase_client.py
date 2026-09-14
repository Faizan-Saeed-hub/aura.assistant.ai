import os
import uuid
import httpx
from typing import Dict, Any, Optional, List
from backend.config import config
from backend.database import (
    create_user_account, get_active_user, update_user_profile,
    get_connection, DEFAULT_MALE_AVATAR, DEFAULT_FEMALE_AVATAR
)

class SupabaseAuthManager:
    """
    Supabase Cloud Authentication & User Profile Manager:
    - Direct integration with Supabase Auth API (when SUPABASE_URL & ANON_KEY are present).
    - Seamless fallback to local persistent account engine for local deployment & development.
    - Manages user-specific BYOK (Bring Your Own Key) personal API keys.
    """

    def __init__(self):
        self.url = config.SUPABASE_URL.rstrip("/")
        self.anon_key = config.SUPABASE_ANON_KEY

    def is_configured(self) -> bool:
        return bool(self.url and self.anon_key and "supabase.co" in self.url)

    async def signup(self, email: str, password: str, name: str, role: str = "Creator", gender: str = "male", avatar_url: Optional[str] = None) -> Dict[str, Any]:
        default_avatar = DEFAULT_MALE_AVATAR if gender == "male" else DEFAULT_FEMALE_AVATAR
        final_avatar = avatar_url or default_avatar

        if self.is_configured():
            try:
                headers = {
                    "apikey": self.anon_key,
                    "Content-Type": "application/json"
                }
                payload = {
                    "email": email,
                    "password": password,
                    "data": {
                        "name": name,
                        "role": role,
                        "gender": gender,
                        "avatar_url": final_avatar
                    }
                }
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(f"{self.url}/auth/v1/signup", headers=headers, json=payload)
                    data = resp.json()
                    if resp.status_code in [200, 201]:
                        # Save local record for seamless offline caching
                        user_rec = create_user_account(name=name, email=email, password=password, role=role, avatar_url=final_avatar, gender=gender)
                        # Sync to public.profiles if table exists
                        await self.sync_profile_to_db({
                            "auth_user_id": data.get("user", {}).get("id") or str(user_rec.get("id")),
                            "email": email,
                            "name": name,
                            "role": role,
                            "gender": gender,
                            "avatar_url": final_avatar
                        })
                        return {
                            "success": True,
                            "mode": "supabase_cloud",
                            "user": user_rec,
                            "session": data.get("session"),
                            "message": "Account created successfully via Supabase Cloud Auth!"
                        }
                    else:
                        error_msg = data.get("msg") or data.get("error_description") or resp.text
                        # Graceful handling if Supabase email confirmation is rate-limited (3 emails/hr default)
                        if resp.status_code == 429 or "rate limit" in str(error_msg).lower():
                            user_rec = create_user_account(name=name, email=email, password=password, role=role, avatar_url=final_avatar, gender=gender)
                            await self.sync_profile_to_db({
                                "email": email,
                                "name": name,
                                "role": role,
                                "gender": gender,
                                "avatar_url": final_avatar
                            })
                            return {
                                "success": True,
                                "mode": "supabase_local_sync",
                                "user": user_rec,
                                "message": "Account created and ready! (Supabase email confirmation rate-limited; local cloud sync active)"
                            }
                        return {"success": False, "error": error_msg}
            except Exception as e:
                # Fallback to local creation so user is never blocked
                user_rec = create_user_account(name=name, email=email, password=password, role=role, avatar_url=final_avatar, gender=gender)
                return {
                    "success": True,
                    "mode": "local_fallback",
                    "user": user_rec,
                    "message": "Account created successfully (Offline/Local mode)!"
                }

        # Local Dev / Pre-deployment account creation
        user_rec = create_user_account(name=name, email=email, password=password, role=role, avatar_url=final_avatar, gender=gender)
        return {
            "success": True,
            "mode": "local_ready_for_supabase",
            "user": user_rec,
            "token": f"local_sess_{uuid.uuid4().hex[:16]}",
            "message": "Account created successfully! Ready for Supabase Cloud Auth when credentials are provided in .env."
        }

    async def login(self, email: str, password: str) -> Dict[str, Any]:
        if self.is_configured():
            try:
                headers = {
                    "apikey": self.anon_key,
                    "Content-Type": "application/json"
                }
                payload = {
                    "email": email,
                    "password": password
                }
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(f"{self.url}/auth/v1/token?grant_type=password", headers=headers, json=payload)
                    data = resp.json()
                    if resp.status_code == 200:
                        user_info = data.get("user", {})
                        meta = user_info.get("user_metadata", {})
                        user_rec = create_user_account(
                            name=meta.get("name", email.split("@")[0]),
                            email=email,
                            password=password,
                            role=meta.get("role", "Creator"),
                            avatar_url=meta.get("avatar_url", DEFAULT_MALE_AVATAR),
                            gender=meta.get("gender", "male")
                        )
                        return {
                            "success": True,
                            "mode": "supabase_cloud",
                            "user": user_rec,
                            "access_token": data.get("access_token"),
                            "message": "Logged in successfully with Supabase!"
                        }
                    else:
                        # Fallback to local authentication if user exists in local database
                        from backend.database import authenticate_user
                        local_user = authenticate_user(email, password)
                        if local_user:
                            return {
                                "success": True,
                                "mode": "local_fallback",
                                "user": local_user,
                                "token": f"local_sess_{uuid.uuid4().hex[:16]}",
                                "message": "Signed in successfully!"
                            }
                        return {"success": False, "error": data.get("error_description") or data.get("msg") or "Invalid login credentials"}
            except Exception as e:
                from backend.database import authenticate_user
                local_user = authenticate_user(email, password)
                if local_user:
                    return {
                        "success": True,
                        "mode": "local_offline",
                        "user": local_user,
                        "token": f"local_sess_{uuid.uuid4().hex[:16]}",
                        "message": "Signed in successfully (Offline Mode)!"
                    }
                return {"success": False, "error": f"Authentication error: {str(e)}"}

        # Local account match
        from backend.database import authenticate_user
        local_user = authenticate_user(email, password)
        if local_user:
            return {
                "success": True,
                "mode": "local",
                "user": local_user,
                "token": f"local_sess_{uuid.uuid4().hex[:16]}",
                "message": "Signed in successfully!"
            }
        return {"success": False, "error": "Invalid email or password"}

    async def sync_profile_to_db(self, profile_data: Dict[str, Any]) -> bool:
        """Syncs user profile row to public.profiles table in Supabase"""
        if not self.is_configured():
            return False
        try:
            headers = {
                "apikey": self.anon_key,
                "Authorization": f"Bearer {self.anon_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            }
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(f"{self.url}/rest/v1/profiles", headers=headers, json=profile_data)
            return True
        except Exception:
            return False

    async def sync_session_to_db(self, session_id: str, title: str, user_email: Optional[str] = None) -> bool:
        """Syncs or upserts chat session to public.chat_sessions table in Supabase"""
        if not self.is_configured():
            return False
        try:
            headers = {
                "apikey": self.anon_key,
                "Authorization": f"Bearer {self.anon_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            }
            payload = {
                "id": session_id,
                "title": title or "New Chat",
                "user_email": (user_email or "").strip().lower() or None
            }
            async with httpx.AsyncClient(timeout=6) as client:
                resp = await client.post(f"{self.url}/rest/v1/chat_sessions", headers=headers, json=payload)
                return resp.status_code in [200, 201, 204]
        except Exception:
            return False

    async def sync_chat_message_to_db(self, session_id: str, role: str, content: str, user_email: Optional[str] = None, session_title: Optional[str] = None) -> bool:
        """Syncs a chat message to public.chat_messages table in Supabase, guaranteeing parent session exists."""
        if not self.is_configured():
            return False
        try:
            # 1. Ensure parent session exists in Supabase chat_sessions to satisfy foreign key
            await self.sync_session_to_db(session_id, session_title or "Aura Chat", user_email=user_email)

            # 2. Insert message into public.chat_messages
            headers = {
                "apikey": self.anon_key,
                "Authorization": f"Bearer {self.anon_key}",
                "Content-Type": "application/json"
            }
            async with httpx.AsyncClient(timeout=6) as client:
                resp = await client.post(f"{self.url}/rest/v1/chat_messages", headers=headers, json={
                    "session_id": session_id,
                    "role": role,
                    "content": content
                })
                return resp.status_code in [200, 201, 204]
        except Exception:
            return False

    async def get_cloud_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieves cloud chat messages from public.chat_messages table in Supabase"""
        if not self.is_configured():
            return []
        try:
            headers = {
                "apikey": self.anon_key,
                "Authorization": f"Bearer {self.anon_key}"
            }
            async with httpx.AsyncClient(timeout=6) as client:
                resp = await client.get(
                    f"{self.url}/rest/v1/chat_messages?session_id=eq.{session_id}&order=created_at.asc",
                    headers=headers
                )
                if resp.status_code == 200:
                    return resp.json()
                return []
        except Exception:
            return []

    async def get_cloud_sessions(self, user_email: str) -> List[Dict[str, Any]]:
        """Retrieves user chat sessions from public.chat_sessions in Supabase"""
        if not self.is_configured() or not user_email:
            return []
        try:
            headers = {
                "apikey": self.anon_key,
                "Authorization": f"Bearer {self.anon_key}"
            }
            async with httpx.AsyncClient(timeout=6) as client:
                resp = await client.get(
                    f"{self.url}/rest/v1/chat_sessions?user_email=eq.{user_email.strip().lower()}&order=updated_at.desc",
                    headers=headers
                )
                if resp.status_code == 200:
                    return resp.json()
                return []
        except Exception:
            return []

    async def check_cloud_tables_status(self) -> Dict[str, Any]:
        """Checks readiness of all Supabase Cloud tables: profiles, chat_sessions, chat_messages, user_notes"""
        if not self.is_configured():
            return {
                "configured": False,
                "url": self.url,
                "status": "Not Configured",
                "tables": {}
            }
        headers = {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {self.anon_key}"
        }
        table_names = ["profiles", "chat_sessions", "chat_messages", "user_notes"]
        tables_status = {}
        all_ready = True
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                for tbl in table_names:
                    r = await client.get(f"{self.url}/rest/v1/{tbl}?select=id&limit=1", headers=headers)
                    if r.status_code in [200, 206]:
                        tables_status[tbl] = "ready"
                    elif r.status_code == 404 or "not find" in r.text.lower():
                        tables_status[tbl] = "table_missing"
                        all_ready = False
                    else:
                        tables_status[tbl] = f"error_{r.status_code}"
                        all_ready = False
            return {
                "configured": True,
                "url": self.url,
                "all_ready": all_ready,
                "tables": tables_status
            }
        except Exception as e:
            return {
                "configured": True,
                "url": self.url,
                "all_ready": False,
                "error": str(e),
                "tables": tables_status
            }

    async def sync_note_to_db(self, title: str, content: str, user_email: Optional[str] = None) -> bool:
        """Syncs a note to public.user_notes table in Supabase"""
        if not self.is_configured():
            return False
        try:
            headers = {
                "apikey": self.anon_key,
                "Authorization": f"Bearer {self.anon_key}",
                "Content-Type": "application/json"
            }
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(f"{self.url}/rest/v1/user_notes", headers=headers, json={
                    "user_email": user_email or "faizanbarvi786@gmail.com",
                    "title": title,
                    "content": content,
                    "status": "pending"
                })
            return True
        except Exception:
            return False

    async def delete_user_from_cloud(self, email: str) -> Dict[str, Any]:
        """Deletes user records from Supabase tables (profiles, chat_sessions, user_notes)"""
        if not self.is_configured():
            return {"success": False, "error": "Supabase not configured"}
        headers = {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {self.anon_key}",
            "Content-Type": "application/json"
        }
        deleted_tables = []
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                # 1. Delete from profiles table
                r1 = await client.delete(f"{self.url}/rest/v1/profiles?email=eq.{email}", headers=headers)
                if r1.status_code in [200, 204]:
                    deleted_tables.append("profiles")
                # 2. Delete from chat_sessions table
                r2 = await client.delete(f"{self.url}/rest/v1/chat_sessions?user_email=eq.{email}", headers=headers)
                if r2.status_code in [200, 204]:
                    deleted_tables.append("chat_sessions")
                # 3. Delete from user_notes table
                r3 = await client.delete(f"{self.url}/rest/v1/user_notes?user_email=eq.{email}", headers=headers)
                if r3.status_code in [200, 204]:
                    deleted_tables.append("user_notes")
            return {
                "success": True,
                "deleted_tables": deleted_tables,
                "message": f"User {email} records cleaned up from Supabase Cloud"
            }
        except Exception as e:
            return {"success": False, "error": f"Supabase delete failed: {str(e)}"}

supabase_auth = SupabaseAuthManager()
