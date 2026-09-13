import math

def calculate(expression: str) -> str:
    """Safely calculate mathematical expressions including trigonometric, logarithmic, and power functions."""
    allowed_names = {
        k: v for k, v in math.__dict__.items() if not k.startswith("__")
    }
    allowed_names.update({
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow
    })
    
    # Clean expression
    cleaned = expression.replace("^", "**").strip()
    try:
        # Check for dangerous builtins
        code = compile(cleaned, "<string>", "eval")
        for name in code.co_names:
            if name not in allowed_names:
                return f"Error: Function or name '{name}' is not allowed in calculations."
        
        result = eval(code, {"__builtins__": {}}, allowed_names)
        return f"Result: {result}"
    except Exception as e:
        return f"Calculation error for '{expression}': {str(e)}"
