import os
import uuid
import httpx
from typing import Dict, Any, Optional
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
                        return {
                            "success": True,
                            "mode": "supabase_cloud",
                            "user": user_rec,
                            "session": data.get("session"),
                            "message": "Account created successfully via Supabase Cloud Auth!"
                        }
                    else:
                        error_msg = data.get("msg") or data.get("error_description") or resp.text
                        return {"success": False, "error": error_msg}
            except Exception as e:
                return {"success": False, "error": f"Supabase connection error: {str(e)}"}

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
                        return {"success": False, "error": data.get("error_description", "Invalid login credentials")}
            except Exception as e:
                return {"success": False, "error": f"Supabase auth error: {str(e)}"}

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

supabase_auth = SupabaseAuthManager()
