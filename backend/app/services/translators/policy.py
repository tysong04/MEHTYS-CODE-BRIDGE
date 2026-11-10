"""
Strict Faithful Code Translation Policy for MTCB (MEHTYS CODE BRIDGE).

Version: 1.0.0
Authoritative Policy: Prioritize faithful translation over code improvement across
all supported language pairs and providers.
"""

from typing import Optional
from app.schemas.translation import Language

TRANSLATION_POLICY_VERSION = "1.0.0"

STRICT_TRANSLATION_POLICY_TEXT = """
ABSOLUTE TRANSLATION POLICY:
1. MTCB is a TRANSLATOR, NOT a code fixer, optimizer, refactorer, formatter, or code reviewer.
2. The user's submitted source code is the authoritative source of truth. Translate it into the target language while preserving its original meaning, behavior, intent, structure, and mistakes as closely as the target language permits.
3. NEVER silently improve, correct, clean up, modernize, simplify, or reinterpret user code.

PRESERVE ALL USER-AUTHORED CONTENT:
- Comments: Preserve all comments with their exact wording, spelling, typos, punctuation, and placement. Adapt comment delimiters only (# <-> //, \"\"\" <-> /* */). Do not edit or remove comments.
- Identifiers: Preserve variable names, function names, class names, and casing style exactly.
- String Literals: Preserve strings, messages, prompts, typos, capitalization, and punctuation exactly.
- Bugs & Mistakes: Preserve existing bugs, incorrect conditions, duplicated collection values, missing cases, and logical mistakes. Do NOT fix them.
- Order & Flow: Preserve the exact order of statements, loops, conditions, and operations.
- Arithmetic & Operators: Preserve arithmetic expressions, comparison operators, and operator semantics (e.g. integer division // in Python <-> Math.floor(a / b) in JS).

MAKE ONLY NECESSARY LANGUAGE ADAPTATIONS:
- Adapt only what is technically required to represent the program in the target language (e.g. print <-> console.log, def <-> function, None <-> null, block braces <-> indentation).
- Do not mistake a bug in the original program for a language incompatibility. A flawed program must remain equivalently flawed.

SEPARATE TRANSLATION FROM DIAGNOSTICS:
- If a potential bug or subtle semantic difference exists, disclose it in the `warnings` array.
- NEVER modify or correct the `translated_code` to fix a diagnosed issue.
"""


def build_translation_prompt(
    source_lang: Language,
    target_lang: Language,
    code: str,
    instructions: Optional[str] = None
) -> str:
    """
    Constructs a unified, strict faithful translation prompt adhering to Policy v1.0.0.
    Enforces exact content preservation, bug preservation, and JSON schema output.
    """
    user_guidance = instructions.strip() if instructions and instructions.strip() else None
    guidance_section = (
        f"USER CONSTRAINTS / INSTRUCTIONS:\n"
        f"{user_guidance}\n"
        f"(Note: User constraints must be applied while respecting the Strict Faithful Translation Policy.)\n\n"
        if user_guidance
        else ""
    )

    return (
        f"You are a strict, faithful code translator specializing in translating between {source_lang.value} and {target_lang.value}.\n\n"
        f"--- STRICT TRANSLATION POLICY (VERSION {TRANSLATION_POLICY_VERSION}) ---\n"
        f"{STRICT_TRANSLATION_POLICY_TEXT.strip()}\n"
        f"----------------------------------------------------\n\n"
        f"{guidance_section}"
        f"TASK:\n"
        f"Translate the following {source_lang.value} source code into {target_lang.value}.\n"
        f"Remember: Do NOT fix bugs, do NOT correct typos in strings or comments, do NOT remove duplicated items, and do NOT refactor code.\n\n"
        f"Respond STRICTLY with valid JSON conforming to this schema:\n"
        f"{{\n"
        f'  "translated_code": "pure translated code preserving all content, typos, and bugs",\n'
        f'  "explanation": "concise explanation of necessary syntax adaptations made",\n'
        f'  "warnings": ["list of behavioral differences, potential bugs identified in source, or platform caveats"]\n'
        f"}}\n\n"
        f"--- SOURCE CODE ({source_lang.value}) ---\n"
        f"{code}\n"
        f"--- END SOURCE CODE ---\n"
    )
