import json
from typing import List, Dict, Any, Callable
from backend.tools.web_search import web_search
from backend.tools.weather import get_weather
from backend.tools.calculator import calculate
from backend.tools.notes import add_note, list_notes, complete_note, delete_note
from backend.tools.system_info import get_system_info
from backend.tools.wikipedia import wikipedia_lookup

# Standard tool definitions schema for LLMs
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Perform a real-time live web search using DuckDuckGo to find current news, facts, articles, and websites (100% Free).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query, e.g. 'latest AI news' or 'Python 3.12 release notes'"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get real-time weather and forecast for any city or location in the world (100% Free).",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City or location name, e.g. 'London', 'Tokyo', 'Islamabad', 'San Francisco'"
                    }
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate mathematical expressions, trigonometry, square roots, logarithms, powers, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical formula to evaluate, e.g. '24 * 12 + sqrt(144)' or 'pow(2, 10)'"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "wikipedia_lookup",
            "description": "Search and retrieve a concise factual summary of any topic, person, place, or concept from Wikipedia (100% Free).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The topic or subject to lookup, e.g. 'Quantum Computing' or 'Albert Einstein'"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Get the current real-world date, time, weekday, timezone, and system info.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_note",
            "description": "Save a personal note or reminder for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title or subject of the note"},
                    "content": {"type": "string", "description": "Optional details or body of the note"},
                    "due_date": {"type": "string", "description": "Optional due date or time, e.g. 'Tomorrow 5 PM'"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_notes",
            "description": "View pending or completed notes and reminders.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "completed", "all"],
                        "description": "Filter status: 'pending' (default), 'completed', or 'all'"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete_note",
            "description": "Mark a note or reminder as finished by its ID number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "note_id": {"type": "integer", "description": "The numeric ID of the note to complete"}
                },
                "required": ["note_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remember_fact",
            "description": "Store a personal fact, habit, detail, or preference about the user in permanent long-term memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {
                        "type": "string",
                        "description": "The fact or preference to remember, e.g. 'User is named Muhammad Faizan' or 'User prefers dark mode'"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["fact", "preference", "project", "rule"],
                        "description": "Category of memory (default: 'fact')"
                    }
                },
                "required": ["fact"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "forget_memory",
            "description": "Delete a personal fact or memory from long-term memory by its ID number or matching phrase/keyword.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_or_id": {
                        "type": "string",
                        "description": "The numeric ID or search keyword/phrase of the memory to remove"
                    }
                },
                "required": ["query_or_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Generate high-resolution AI artwork, photos, or concept art from a descriptive text prompt using Pollinations AI (100% Free, instant).",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Visual prompt describing the image to generate, e.g. 'futuristic sports car in neon city at night, 8k resolution, cinematic lighting'"
                    }
                },
                "required": ["prompt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_memories",
            "description": "List all active long-term memories and facts stored about the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of memories to return (default: 10)"
                    }
                }
            }
        }
    }
]

from backend.memory.long_term import long_term_memory
from backend.tools.image_studio import generate_ai_image

def tool_generate_image(prompt: str) -> str:
    res = generate_ai_image(prompt)
    if res.get("success"):
        return f"AI Image generated successfully!\n\n![{prompt}]({res['image_url']})\n\n[Open Full Size Image]({res['image_url']})"
    return f"Failed to generate image: {res.get('error', 'Unknown error')}"

def tool_remember_fact(fact: str, category: str = "fact") -> str:
    if not fact or not str(fact).strip():
        return "No fact provided to remember."
    mem_id = long_term_memory.add(category=category or "fact", content=str(fact).strip(), importance=4, source="explicit_user")
    return f"Successfully saved to permanent memory (ID: {mem_id}): '{str(fact).strip()}'"

def tool_forget_memory(query_or_id: str) -> str:
    q = str(query_or_id).strip()
    if not q:
        return "Please specify the memory ID or text phrase to forget."
    if q.isdigit():
        success = long_term_memory.delete(int(q))
        return f"Memory ID {q} was successfully removed." if success else f"Memory ID {q} not found."
    count = long_term_memory.delete_by_query(q)
    if count > 0:
        return f"Successfully deleted {count} memory item(s) matching '{q}'."
    return f"No memories found matching '{q}'."

def tool_list_memories(limit: int = 10) -> str:
    mems = long_term_memory.get_all(limit=limit or 10)
    if not mems:
        return "No personal memories currently stored."
    lines = ["Saved Personal Memories:"]
    for m in mems:
        lines.append(f"- ID {m['id']} [{m['category']}]: {m['content']}")
    return "\n".join(lines)

TOOL_FUNCTIONS: Dict[str, Callable] = {
    "web_search": lambda args: web_search(args.get("query", "")),
    "get_weather": lambda args: get_weather(args.get("location", "")),
    "calculate": lambda args: calculate(args.get("expression", "")),
    "wikipedia_lookup": lambda args: wikipedia_lookup(args.get("query", "")),
    "get_system_info": lambda args: get_system_info(),
    "add_note": lambda args: add_note(args.get("title", ""), args.get("content", ""), args.get("due_date", "")),
    "list_notes": lambda args: list_notes(args.get("status", "pending")),
    "complete_note": lambda args: complete_note(args.get("note_id", 0)),
    "remember_fact": lambda args: tool_remember_fact(args.get("fact", ""), args.get("category", "fact")),
    "forget_memory": lambda args: tool_forget_memory(args.get("query_or_id", "")),
    "list_memories": lambda args: tool_list_memories(args.get("limit", 10)),
    "generate_image": lambda args: tool_generate_image(args.get("prompt", "")),
}

def execute_tool(name: str, arguments: Any) -> str:
    """Execute a registered tool by name with arguments dict or json string."""
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except Exception:
            arguments = {}
            
    fn = TOOL_FUNCTIONS.get(name)
    if not fn:
        return f"Tool '{name}' is not recognized."
    
    try:
        return str(fn(arguments or {}))
    except Exception as e:
        return f"Error executing tool '{name}': {str(e)}"

