import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from backend.config import config
from backend.memory.conversation import conversation_manager
from backend.memory.long_term import long_term_memory
from backend.rag.vector_store import vector_store
from backend.llm.client import llm_client
from backend.llm.prompts import SYSTEM_PERSONA_PROMPT

from backend.database import get_active_user

class AgentOrchestrator:
    """Coordinates Conversation Context, Long-Term Memory, RAG, Tool Execution, and LLMs."""

    async def process_message(
        self,
        session_id: str,
        user_message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        # 1. Save user message to short-term history
        conversation_manager.append_message(session_id, "user", user_message)

        # 2. Retrieve conversation history
        history = conversation_manager.get_context(session_id)

        # 3. Retrieve active user profile (Identity)
        active_user = get_active_user()
        user_name = active_user.get("name", "User")
        user_email = active_user.get("email", "")
        user_role = active_user.get("role", "Personal AI User")
        user_bio = active_user.get("bio", "")
        user_gender = active_user.get("gender", "male")

        user_identity_context = (
            f"### Active User Profile (Your Owner & Creator):\n"
            f"- Full Name: {user_name}\n"
            f"- Email: {user_email}\n"
            f"- Role / Title: {user_role}\n"
            f"- Gender: {user_gender}\n"
            f"- Background / Bio: {user_bio or 'Personal user'}\n\n"
            f"CRITICAL INSTRUCTION: You are the dedicated personal assistant to **{user_name}**. You ALREADY know their name and identity! "
            f"Never state that you do not know their name. If the user asks 'who am I?', 'what is my name?', or in Roman Urdu 'mera naam kya hai?', "
            f"answer clearly and accurately that their name is {user_name}.\n"
            f"If the user tells you to remember a fact or preference, call the `remember_fact` tool. "
            f"If the user tells you to forget, remove, or delete something from memory, call the `forget_memory` tool."
        )

        # 4. Retrieve long-term memory
        memory_context = long_term_memory.format_for_prompt()

        # 5. Perform RAG retrieval for relevant document chunks (require at least 25% match)
        rag_results = vector_store.search(user_message, top_k=config.TOP_K_RETRIEVAL, min_score=0.25)
        rag_context = ""
        citations = []

        if rag_results:
            rag_lines = ["[Knowledge Base Document Context (RAG)]"]
            for r in rag_results:
                if r.get("score", 0) >= 0.25:
                    src_label = f"{r['filename']} (Page {r.get('page', 1)})"
                    rag_lines.append(f"--- Document Source: {src_label} (Relevance: {int(r['score']*100)}%) ---")
                    rag_lines.append(r["text"])
                    citations.append({
                        "filename": r["filename"],
                        "page": r.get("page", 1),
                        "score": r["score"],
                        "snippet": r["text"][:140] + "..." if len(r["text"]) > 140 else r["text"]
                    })
            if citations:
                rag_context = "\n".join(rag_lines)

        # 6. Determine active provider & model for system awareness
        active_prov = provider or llm_client.get_active_provider()
        active_mod = model or llm_client.get_active_model(active_prov)

        runtime_awareness = (
            f"### Active Runtime AI Configuration:\n"
            f"- Current Active Provider: {active_prov.upper()}\n"
            f"- Current Active Model: {active_mod}\n\n"
            f"CRITICAL INSTRUCTION: If the user asks what model, engine, or provider is currently running, working, or powering you, "
            f"state clearly and explicitly that you are running on **{active_mod}** via **{active_prov.upper()}**."
        )

        system_prompt_parts = [SYSTEM_PERSONA_PROMPT, user_identity_context, runtime_awareness]
        if memory_context:
            system_prompt_parts.append("\n" + memory_context)
        if rag_context:
            system_prompt_parts.append("\n" + rag_context)

        full_system_prompt = "\n\n".join(system_prompt_parts)

        # 6. Execute LLM generation with agentic tool loop
        response_data = await llm_client.generate_response(
            messages=history,
            system_prompt=full_system_prompt,
            provider=provider,
            model=model,
            tools_enabled=True
        )

        assistant_text = response_data.get("text", "")
        tool_calls = response_data.get("tool_calls", [])

        # 7. Save assistant reply to database
        conversation_manager.append_message(
            session_id,
            "assistant",
            assistant_text,
            tool_calls=tool_calls,
            citations=citations
        )

        # 8. Background task: extract long-term facts asynchronously
        asyncio.create_task(
            self._extract_memory_bg(user_message, assistant_text, provider, model)
        )

        return {
            "text": assistant_text,
            "tool_calls": tool_calls,
            "citations": citations
        }

    async def _extract_memory_bg(self, user_msg: str, assistant_reply: str, provider: str, model: str):
        """Asynchronously analyze user statement to store enduring facts."""
        try:
            async def generate_helper(prompt: str, system_instruction: str = ""):
                res = await llm_client.generate_response(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt=system_instruction,
                    provider=provider,
                    model=model,
                    tools_enabled=False
                )
                return res.get("text", "")

            await long_term_memory.extract_facts_from_turn(user_msg, assistant_reply, generate_helper)
        except Exception:
            pass

agent_orchestrator = AgentOrchestrator()
