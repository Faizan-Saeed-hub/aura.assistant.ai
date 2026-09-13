import os
import json
import asyncio
import httpx
from typing import List, Dict, Any, AsyncGenerator, Optional
from backend.config import config
from backend.database import get_setting
from backend.tools.registry import TOOLS_SCHEMA, execute_tool

class LLMClient:
    """Unified LLM client supporting Google Gemini, Groq, OpenAI, and Ollama."""

    def get_api_key(self, provider: str) -> str:
        """Get API key from database runtime settings or environment/config."""
        db_key = get_setting(f"{provider.upper()}_API_KEY", "")
        if db_key:
            return db_key
        if provider == "openrouter":
            return config.OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY", "")
        elif provider == "gemini":
            return config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        elif provider == "groq":
            return config.GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")
        elif provider == "openai":
            return config.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
        return ""

    def get_active_provider(self) -> str:
        return get_setting("ACTIVE_PROVIDER", config.DEFAULT_PROVIDER)

    def get_active_model(self, provider: str) -> str:
        default_model = config.get_active_model(provider)
        model = get_setting(f"{provider.upper()}_MODEL", default_model)
        if provider == "groq" and ("versatile" in model or "compound" in model or "120b" in model):
            return "openai/gpt-oss-20b"
        return model

    def _fallback_local_response(self, user_msg: str) -> Dict[str, Any]:
        import re
        msg = user_msg.lower().strip()
        
        is_roman_urdu = bool(re.search(r'[\u0600-\u06FF]', user_msg)) or any(
            w in msg for w in [
                "kya", "kaise", "kaisay", "haal", "hal", "kaun", "kon", "kaisa", "kaisi", 
                "batao", "mausam", "salam", "shukriya", "bhai", "aaj", "waqt", "chal raha", 
                "aap", "ap", "tum", "mujhe", "mera", "meri", "hum", "theek", "shukran"
            ]
        )
        
        # Greetings
        if any(w in msg for w in ["hey", "hello", "hi", "hey aura", "hello aura", "hi aura", "how are you", "what's up", "yo", "kya haal", "kaise ho", "salam", "assalam"]):
            if is_roman_urdu:
                return {
                    "text": "👋 **Assalam-o-Alaikum! Main Aura hoon, aap ka AI Personal Assistant!**\n\nMain bilkul theek hoon aur aap ki madad ke liye tayyar hoon. Aap mujh se Roman Urdu ya English mein baat kar sakte hain:\n- 🌤️ *\"Karachi ka mausam kaisa hai?\"*\n- 🧮 *\"Calculate 45 * 80 + sqrt(144)\"*\n- ⏰ *\"Waqt kya hua hai?\"*\n- 🤖 *\"Kaun sa model chal raha hai?\"*\n- 📚 *Knowledge Base mein documents upload kar ke sawal poochein!*\n\nMain aap ke liye kya kar sakta hoon?",
                    "tool_calls": []
                }
            return {
                "text": "👋 **Hello! I'm Aura, your AI Personal Assistant!**\n\nI'm active, responsive, and ready to assist you in English or Roman Urdu. You can try out my built-in tools right away:\n- 🌤️ *\"What is the weather in Islamabad?\"*\n- 🧮 *\"Calculate 45 * 80 + sqrt(144)\"*\n- ⏰ *\"What time is it?\"*\n- 🤖 *\"Which model are you using?\"*\n- 📚 *Upload a PDF/TXT in Knowledge Base for instant document RAG!*\n\nHow can I help you today?",
                "tool_calls": []
            }

        # Check for active model/provider inquiry
        if any(w in msg for w in ["which model", "what model", "which provider", "what provider", "who powers you", "model are you", "what engine", "kaun sa model", "kon sa model", "model batao"]):
            prov = self.get_active_provider()
            mod = self.get_active_model(prov)
            if is_roman_urdu:
                return {
                    "text": f"🤖 **Active AI Engine Ki Maloomat:**\n- **Provider:** `{prov.upper()}`\n- **Model:** `{mod}`\n\nMain is waqt is model ke zariye live active hoon aur aap ke sawalat ka jawab de raha hoon!",
                    "tool_calls": []
                }
            return {
                "text": f"🤖 **Active AI Engine:**\n- **Provider:** `{prov.upper()}`\n- **Model:** `{mod}`\n\nI am currently running on this model with multi-provider failover and real-time tools!",
                "tool_calls": []
            }

        # Check for system time/date
        if any(w in msg for w in ["what time", "current time", "what date", "today's date", "time kya", "waqt kya", "kya time"]):
            out = execute_tool("get_system_info", {})
            header = "🕒 **System Waqt & Tareekh:**" if is_roman_urdu else "🕒 **Here is your system time:**"
            return {"text": f"{header}\n\n{out}", "tool_calls": [{"tool": "get_system_info", "arguments": {}, "output": out}]}

        # Check for weather
        if any(w in msg for w in ["weather", "mausam"]):
            import re
            loc = "Islamabad"
            for city in ["karachi", "lahore", "islamabad", "rawalpindi", "peshawar", "quetta", "multan", "faisalabad", "london", "dubai", "new york", "tokyo"]:
                if city in msg:
                    loc = city.title()
                    break
            if loc == "Islamabad":
                loc_match = re.search(r'(?:in|ka|of)\s+([a-zA-Z\s]+)', msg)
                if loc_match:
                    loc = loc_match.group(1).strip()
            out = execute_tool("get_weather", {"location": loc})
            header = f"🌦️ **{loc} Ka Mausam:**" if is_roman_urdu else f"🌦️ **Weather Report for {loc}:**"
            return {"text": f"{header}\n\n{out}", "tool_calls": [{"tool": "get_weather", "arguments": {"location": loc}, "output": out}]}

        # Check for math
        if any(w in msg for w in ["calculate", "sqrt", "pow", "*", "+"]):
            import re
            expr = re.sub(r'[^0-9\+\-\*\/\.\(\)\^\s]', '', msg)
            if expr.strip():
                out = execute_tool("calculate", {"expression": expr})
                return {"text": f"🧮 **Calculation Result:**\n\n{out}", "tool_calls": [{"tool": "calculate", "arguments": {"expression": expr}, "output": out}]}

        # Default helpful guide
        return {
            "text": "👋 **Welcome to your AI Personal Assistant!**\n\nTo chat freely on any topic, add your **100% Free OpenRouter API key** (or Google Gemini/Groq key) in **Settings (⚙️ icon)**.\n\n- 🌟 **OpenRouter Key (100% Free Models)**: [Get Free Key at openrouter.ai/keys](https://openrouter.ai/keys)\n- ⚡ **Groq Key (Free, Ultra-Fast)**: [Get Key at Groq Console](https://console.groq.com/keys)\n- 💎 **Google Gemini Key (Free)**: [Get Key at Google AI Studio](https://aistudio.google.com/app/apikey)\n\n*You can also use tools directly (e.g. \"weather in Tokyo\", \"what time is it\", or upload documents in the Knowledge Base).* ",
            "tool_calls": []
        }

    async def generate_response(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        tools_enabled: bool = True
    ) -> Dict[str, Any]:
        primary_prov = provider or self.get_active_provider()
        
        # Priority order of providers: primary choice first, then other available providers
        all_providers = ["groq", "openrouter", "gemini", "openai", "ollama"]
        ordered_providers = [primary_prov] + [p for p in all_providers if p != primary_prov]

        last_error = ""
        for prov in ordered_providers:
            key = self.get_api_key(prov)
            # Cloud providers require key (Ollama does not)
            if prov != "ollama" and not key:
                continue

            mod = (model if prov == primary_prov else None) or self.get_active_model(prov)
            
            try:
                if prov == "groq":
                    res = await asyncio.to_thread(self._generate_groq, messages, system_prompt, mod, key, tools_enabled)
                elif prov == "openrouter":
                    res = await asyncio.to_thread(self._generate_openrouter, messages, system_prompt, mod, key, tools_enabled)
                elif prov == "gemini":
                    res = await asyncio.to_thread(self._generate_gemini, messages, system_prompt, mod, key, tools_enabled)
                elif prov == "openai":
                    res = await asyncio.to_thread(self._generate_openai, messages, system_prompt, mod, key, tools_enabled)
                elif prov == "ollama":
                    res = await self._generate_ollama(messages, system_prompt, mod, tools_enabled)
                else:
                    continue

                # Verify if response is successful (not an error string)
                text = res.get("text", "")
                if text and not any(text.startswith(prefix) for prefix in [
                    "Error from", "⚠️ Error", "Could not connect to Ollama", "⚠️ Could not connect"
                ]):
                    return res
                else:
                    last_error = text
                    print(f"[*] Provider '{prov}' returned error, auto-failing over to next available provider...")
            except Exception as e:
                last_error = str(e)
                print(f"[*] Exception with provider '{prov}': {e}. Auto-failing over...")
                continue

        # If all configured providers were exhausted, gracefully fallback to local offline agent tools
        latest_msg = messages[-1]["content"] if messages else ""
        return self._fallback_local_response(latest_msg)

    def _generate_gemini(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        model: str,
        api_key: str,
        tools_enabled: bool
    ) -> Dict[str, Any]:
        """Call Google Gemini API using modern official google-genai SDK."""
        # Priority candidate models with fresh free quotas
        default_order = ["gemini-2.5-flash-lite", "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemma-4-26b-a4b-it", "gemini-2.5-flash"]
        candidates = []
        if model and model not in ["gemini-2.0-flash", "models/gemini-2.0-flash"]:
            candidates.append(model)
        for m in default_order:
            if m not in candidates:
                candidates.append(m)

        from backend.tools.web_search import web_search
        from backend.tools.weather import get_weather
        from backend.tools.calculator import calculate
        from backend.tools.wikipedia import wikipedia_lookup
        from backend.tools.system_info import get_system_info
        from backend.tools.notes import add_note, list_notes, complete_note

        tools_list = [
            web_search,
            get_weather,
            calculate,
            wikipedia_lookup,
            get_system_info,
            add_note,
            list_notes,
            complete_note
        ] if tools_enabled else None

        last_error = None
        for candidate_model in candidates:
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=api_key)

                # Format conversation history
                history_contents = []
                for m in messages[:-1]:
                    role = "user" if m["role"] == "user" else "model"
                    history_contents.append(types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=m["content"])]
                    ))

                latest_user_content = messages[-1]["content"] if messages else ""

                config_kwargs = {
                    "system_instruction": system_prompt
                }
                if tools_list:
                    config_kwargs["tools"] = tools_list

                # Create Chat with Automatic Function Calling
                chat = client.chats.create(
                    model=candidate_model,
                    history=history_contents,
                    config=types.GenerateContentConfig(**config_kwargs)
                )

                response = chat.send_message(latest_user_content)

                # Extract response text safely
                text_out = response.text or ""
                
                # Check executed tools if any
                executed_tools = []
                if hasattr(response, "function_calls") and response.function_calls:
                    for fc in response.function_calls:
                        executed_tools.append({
                            "tool": getattr(fc, "name", "tool"),
                            "arguments": getattr(fc, "args", {})
                        })

                return {"text": text_out, "tool_calls": executed_tools}

            except Exception as e:
                err_str = str(e)
                last_error = err_str
                # If 429 quota reached, 404 model deprecated, or 503 high demand, try the next model seamlessly!
                if any(code in err_str for code in ["429", "RESOURCE_EXHAUSTED", "Quota exceeded", "404", "503", "no longer available", "not found"]):
                    continue
                else:
                    return {"text": f"Error from Google Gemini ({candidate_model}): {err_str}", "tool_calls": []}

        # If all Gemini cloud models are exhausted, fallback smoothly to local tool assistant
        fallback_res = self._fallback_local_response(messages[-1]["content"] if messages else "")
        fallback_res["text"] = f"⏳ *Free API key daily quota was reached on Google AI Studio for this minute. Using offline agent tools:*\n\n" + fallback_res["text"]
        return fallback_res

    def _generate_openrouter(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        model: str,
        api_key: str,
        tools_enabled: bool
    ) -> Dict[str, Any]:
        """Call OpenRouter API with verified working 100% Free models."""
        default_free = [
            "nvidia/nemotron-3.5-lightning:free",
            "nex-agi/nex-n2.5-mini:free",
            "liquid/lfm-2.5-2.6b:free"
        ]
        candidates = []
        if model and not any(m in model for m in ["llama-3.3-70b-instruct:free", "deepseek-r1:free", "gemini-2.0-flash-exp:free"]):
            candidates.append(model)
        for m in default_free:
            if m not in candidates:
                candidates.append(m)
        candidates = candidates[:2]

        from openai import OpenAI
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            timeout=5.0,
            default_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Aura AI Assistant"
            }
        )

        base_msgs = [{"role": "system", "content": system_prompt}]
        for m in messages:
            base_msgs.append({"role": m["role"], "content": m["content"]})

        last_error = None
        for candidate_model in candidates:
            try:
                chat_msgs = [dict(x) for x in base_msgs]
                executed_tools = []
                if tools_enabled:
                    try:
                        response = client.chat.completions.create(
                            model=candidate_model,
                            messages=chat_msgs,
                            tools=TOOLS_SCHEMA,
                            tool_choice="auto",
                            max_tokens=800
                        )
                        msg = response.choices[0].message
                        if msg.tool_calls:
                            try:
                                chat_msgs.append(msg.model_dump(exclude_none=True))
                            except Exception:
                                chat_msgs.append(msg)

                            for tc in msg.tool_calls:
                                t_name = tc.function.name
                                try:
                                    t_args = json.loads(tc.function.arguments)
                                except Exception:
                                    t_args = {}
                                t_output = execute_tool(t_name, t_args)
                                executed_tools.append({"tool": t_name, "arguments": t_args, "output": t_output})
                                chat_msgs.append({
                                    "role": "tool",
                                    "tool_call_id": tc.id,
                                    "name": t_name,
                                    "content": str(t_output)
                                })
                            synth_res = client.chat.completions.create(
                                model=candidate_model,
                                messages=chat_msgs,
                                max_tokens=800
                            )
                            return {"text": synth_res.choices[0].message.content or "", "tool_calls": executed_tools}
                        return {"text": msg.content or "", "tool_calls": []}
                    except Exception:
                        clean_msgs = [dict(x) for x in base_msgs]
                        response = client.chat.completions.create(
                            model=candidate_model,
                            messages=clean_msgs,
                            max_tokens=800
                        )
                        return {"text": response.choices[0].message.content or "", "tool_calls": []}
                else:
                    response = client.chat.completions.create(
                        model=candidate_model,
                        messages=chat_msgs,
                        max_tokens=800
                    )
                    return {"text": response.choices[0].message.content or "", "tool_calls": []}
            except Exception as e:
                last_error = str(e)
                continue

        return {"text": f"Error from OpenRouter: {last_error}", "tool_calls": []}

    def _generate_groq(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        model: str,
        api_key: str,
        tools_enabled: bool
    ) -> Dict[str, Any]:
        """Call Groq API with ultra-fast models and automatic candidate failover."""
        from groq import Groq
        client = Groq(api_key=api_key, timeout=8.0)

        if tools_enabled:
            default_groq_models = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
        else:
            default_groq_models = ["groq/compound-mini", "qwen/qwen3.6-27b"]

        candidates = []
        if model and "versatile" not in model:
            candidates.append(model)
        for m in default_groq_models:
            if m not in candidates:
                candidates.append(m)

        base_msgs = [{"role": "system", "content": system_prompt}]
        for m in messages:
            base_msgs.append({"role": m["role"], "content": m["content"]})

        last_error = None
        for candidate_model in candidates:
            try:
                chat_msgs = [dict(x) for x in base_msgs]
                executed_tools = []
                
                if tools_enabled:
                    try:
                        response = client.chat.completions.create(
                            model=candidate_model,
                            messages=chat_msgs,
                            tools=TOOLS_SCHEMA,
                            tool_choice="auto",
                            max_tokens=800
                        )
                        msg = response.choices[0].message
                        if msg.tool_calls:
                            try:
                                chat_msgs.append(msg.model_dump(exclude_none=True))
                            except Exception:
                                chat_msgs.append(msg)

                            for tc in msg.tool_calls:
                                t_name = tc.function.name
                                try:
                                    t_args = json.loads(tc.function.arguments)
                                except Exception:
                                    t_args = {}
                                t_output = execute_tool(t_name, t_args)
                                executed_tools.append({"tool": t_name, "arguments": t_args, "output": t_output})
                                chat_msgs.append({
                                    "role": "tool",
                                    "tool_call_id": tc.id,
                                    "name": t_name,
                                    "content": str(t_output)
                                })
                            
                            synth_response = client.chat.completions.create(
                                model=candidate_model,
                                messages=chat_msgs,
                                max_tokens=800
                            )
                            return {"text": synth_response.choices[0].message.content or "", "tool_calls": executed_tools}
                        
                        return {"text": msg.content or "", "tool_calls": []}
                    except Exception as err:
                        err_str = str(err)
                        # If Groq returns tool_use_failed with a parsed tool call
                        if "failed_generation" in err_str:
                            try:
                                import re
                                match = re.search(r"'failed_generation':\s*['\"](\{.*?\})['\"]", err_str, re.DOTALL)
                                if match:
                                    t_data = json.loads(match.group(1))
                                    t_name = t_data.get("name")
                                    t_args = t_data.get("arguments", {})
                                    if isinstance(t_args, str):
                                        t_args = json.loads(t_args)
                                    t_out = execute_tool(t_name, t_args)
                                    return {
                                        "text": f"✅ {t_out}",
                                        "tool_calls": [{"tool": t_name, "arguments": t_args, "output": t_out}]
                                    }
                            except Exception:
                                pass

                        # Otherwise fallback to pure conversation model
                        clean_msgs = [dict(x) for x in base_msgs]
                        fallback_model = "groq/compound-mini"
                        response = client.chat.completions.create(
                            model=fallback_model,
                            messages=clean_msgs,
                            max_tokens=800
                        )
                        return {"text": response.choices[0].message.content or "", "tool_calls": []}
                else:
                    response = client.chat.completions.create(
                        model=candidate_model,
                        messages=chat_msgs,
                        max_tokens=800
                    )
                    return {"text": response.choices[0].message.content or "", "tool_calls": []}

            except Exception as e:
                last_error = str(e)
                continue

        return {"text": f"Error from Groq: {last_error}", "tool_calls": []}

    def _generate_openai(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        model: str,
        api_key: str,
        tools_enabled: bool
    ) -> Dict[str, Any]:
        """Call OpenAI API."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            chat_msgs = [{"role": "system", "content": system_prompt}]
            for m in messages:
                chat_msgs.append({"role": m["role"], "content": m["content"]})

            executed_tools = []
            if tools_enabled:
                response = client.chat.completions.create(
                    model=model,
                    messages=chat_msgs,
                    tools=TOOLS_SCHEMA,
                    tool_choice="auto"
                )
                msg = response.choices[0].message
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        t_name = tc.function.name
                        try:
                            t_args = json.loads(tc.function.arguments)
                        except Exception:
                            t_args = {}
                        t_output = execute_tool(t_name, t_args)
                        executed_tools.append({"tool": t_name, "arguments": t_args, "output": t_output})
                        
                        chat_msgs.append(msg)
                        chat_msgs.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": t_output
                        })
                    
                    synth_res = client.chat.completions.create(
                        model=model,
                        messages=chat_msgs
                    )
                    return {"text": synth_res.choices[0].message.content, "tool_calls": executed_tools}
                return {"text": msg.content or "", "tool_calls": []}
            else:
                response = client.chat.completions.create(
                    model=model,
                    messages=chat_msgs
                )
                return {"text": response.choices[0].message.content or "", "tool_calls": []}

        except Exception as e:
            return {"text": f"Error from OpenAI ({model}): {str(e)}", "tool_calls": []}

    async def _generate_ollama(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        model: str,
        tools_enabled: bool
    ) -> Dict[str, Any]:
        """Call local Ollama instance (100% Free, Offline)."""
        try:
            url = f"{config.OLLAMA_BASE_URL}/api/chat"
            chat_msgs = [{"role": "system", "content": system_prompt}]
            for m in messages:
                chat_msgs.append({"role": m["role"], "content": m["content"]})

            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(url, json={
                    "model": model,
                    "messages": chat_msgs,
                    "stream": False
                })
                if res.status_code == 200:
                    data = res.json()
                    return {"text": data.get("message", {}).get("content", ""), "tool_calls": []}
                else:
                    return {"text": f"Ollama error ({res.status_code}): Ensure Ollama is running locally at {config.OLLAMA_BASE_URL}.", "tool_calls": []}
        except Exception as e:
            return {
                "text": f"⚠️ **Could not connect to local Ollama at `{config.OLLAMA_BASE_URL}`.**\n\nOllama is an offline desktop engine. If you haven't started Ollama on your computer, please open **Settings (⚙️)** and switch your Active Provider to **Groq** (Free & Fast) or **OpenRouter**.",
                "tool_calls": []
            }

llm_client = LLMClient()
