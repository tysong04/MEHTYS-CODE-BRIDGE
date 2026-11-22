"""
MTCB Translation Analysis and Efficiency Engine.
Performs deterministic, defensible static code analysis to compare structural preservation,
content retention, and heuristic semantic fidelity between source and translated code.
Does NOT generate arbitrary or random percentages.
"""

import re
from typing import Dict, Any, Set, List

PYTHON_KEYWORDS = {
    "False", "None", "True", "and", "as", "assert", "async", "await", "break",
    "class", "continue", "def", "del", "elif", "else", "except", "finally",
    "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal",
    "not", "or", "pass", "raise", "return", "try", "while", "with", "yield"
}

JS_KEYWORDS = {
    "break", "case", "catch", "class", "const", "continue", "debugger", "default",
    "delete", "do", "else", "export", "extends", "finally", "for", "function",
    "if", "import", "in", "instanceof", "new", "return", "super", "switch",
    "this", "throw", "try", "typeof", "var", "void", "while", "with", "yield",
    "let", "static", "enum", "await", "async", "null", "undefined", "true", "false"
}


def _extract_identifiers(code: str, lang: str) -> Set[str]:
    """Extract user-defined identifiers (variables, functions), filtering out language keywords."""
    tokens = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", code)
    keywords = PYTHON_KEYWORDS if lang == "python" else JS_KEYWORDS
    # Also ignore standard built-ins for cleaner user-code extraction
    builtins = {"console", "log", "print", "len", "range", "str", "int", "float", "Math", "floor", "ceil", "Array", "Object"}
    return {t for t in tokens if t not in keywords and t not in builtins and len(t) > 1}


def _extract_strings(code: str) -> List[str]:
    """Extract literal string values from code."""
    matches = re.findall(r'(?:"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')', code)
    # Return string contents without quotes
    return [m[1:-1] for m in matches if len(m) > 2]


def _extract_comments(code: str, lang: str) -> List[str]:
    """Extract comment contents."""
    if lang == "python":
        matches = re.findall(r"#.*$", code, flags=re.MULTILINE)
        return [m.lstrip("#").strip() for m in matches if m.lstrip("#").strip()]
    else:
        # JS single-line and multi-line comments
        single = re.findall(r"//.*$", code, flags=re.MULTILINE)
        multi = re.findall(r"/\*[\s\S]*?\*/", code)
        return [s.lstrip("/").strip() for s in single if s.lstrip("/").strip()] + multi


def _count_structural_elements(code: str, lang: str) -> Dict[str, int]:
    """Count functions, loops, branches, and return points in code."""
    if lang == "python":
        funcs = len(re.findall(r"^\s*def\s+[a-zA-Z0-9_]+", code, flags=re.MULTILINE))
        loops = len(re.findall(r"^\s*(?:for|while)\s+", code, flags=re.MULTILINE))
        branches = len(re.findall(r"^\s*(?:if|elif|else)\b", code, flags=re.MULTILINE))
        returns = len(re.findall(r"\breturn\b", code))
    else:
        funcs = len(re.findall(r"(?:function\s+[a-zA-Z0-9_]+|(?:const|let|var)\s+[a-zA-Z0-9_]+\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)", code))
        loops = len(re.findall(r"\b(?:for|while)\s*\(", code))
        branches = len(re.findall(r"\b(?:if|else\s+if|else)\b", code))
        returns = len(re.findall(r"\breturn\b", code))

    return {
        "functions": funcs,
        "loops": loops,
        "branches": branches,
        "returns": returns
    }


def analyze_translation(
    source_code: str,
    translated_code: str,
    source_lang: str,
    target_lang: str,
    warnings: List[str] = None
) -> Dict[str, Any]:
    """
    Compute measurable preservation metrics and generate specific, student-friendly 'Know How?' data.
    """
    warnings = warnings or []

    # 1. Structural Preservation
    src_struct = _count_structural_elements(source_code, source_lang)
    tgt_struct = _count_structural_elements(translated_code, target_lang)

    total_src_elements = sum(src_struct.values())
    total_tgt_elements = sum(tgt_struct.values())

    if total_src_elements == 0:
        structural_score = 100 if total_tgt_elements == 0 else max(50, 100 - total_tgt_elements * 15)
    else:
        diff_sum = (
            abs(src_struct["functions"] - tgt_struct["functions"]) +
            abs(src_struct["loops"] - tgt_struct["loops"]) +
            abs(src_struct["branches"] - tgt_struct["branches"]) +
            abs(src_struct["returns"] - tgt_struct["returns"])
        )
        structural_score = max(0, min(100, round(100 * (1 - (diff_sum / max(1, total_src_elements * 1.5))))))

    # 2. Content Preservation
    src_ids = _extract_identifiers(source_code, source_lang)
    tgt_ids = _extract_identifiers(translated_code, target_lang)

    # Identifier retention (case-insensitive and camelCase / snake_case normalized)
    def normalize_name(n: str) -> str:
        return re.sub(r"[_\W]+", "", n).lower()

    norm_src_ids = {normalize_name(n) for n in src_ids}
    norm_tgt_ids = {normalize_name(n) for n in tgt_ids}

    retained_ids = norm_src_ids.intersection(norm_tgt_ids)
    id_ratio = (len(retained_ids) / len(norm_src_ids)) if norm_src_ids else 1.0

    # String literal retention
    src_strings = _extract_strings(source_code)
    tgt_strings = _extract_strings(translated_code)
    retained_strings = [s for s in src_strings if s in tgt_strings]
    string_ratio = (len(retained_strings) / len(src_strings)) if src_strings else 1.0

    # Comment preservation
    src_comments = _extract_comments(source_code, source_lang)
    tgt_comments = _extract_comments(translated_code, target_lang)
    comment_ratio = (min(len(tgt_comments), len(src_comments)) / len(src_comments)) if src_comments else 1.0

    content_score = round(100 * (0.5 * id_ratio + 0.3 * string_ratio + 0.2 * comment_ratio))
    content_score = max(0, min(100, content_score))

    # 3. Semantic Fidelity (Heuristic Static Estimate)
    # Blend of structure and content, penalized by any translator diagnostic warnings
    warning_penalty = min(25, len(warnings) * 8)
    base_semantic = round(0.55 * structural_score + 0.45 * content_score)
    semantic_score = max(10, min(100, base_semantic - warning_penalty))

    return {
        "metrics": {
            "structural_preservation": {
                "score": structural_score,
                "label": f"{structural_score}%",
                "method": "Static AST/Token Inventory",
                "reliable": True,
                "summary": "Measures preservation of functions, loops, branching statements, and return points."
            },
            "content_preservation": {
                "score": content_score,
                "label": f"{content_score}%",
                "method": "Normalized Identifier & Literal Retention",
                "reliable": True,
                "summary": "Measures retention of user variable names, function identifiers, string literals, and comments."
            },
            "semantic_fidelity": {
                "score": semantic_score,
                "label": f"{semantic_score}% (Static Estimate)",
                "method": "Heuristic Static Equivalence",
                "reliable": False,
                "summary": "Static heuristic estimate. Real runtime semantic equivalence requires behavioral execution testing."
            },
            "behavioral_verification": {
                "score": None,
                "label": "Not verified",
                "method": "Input/Output Execution Test",
                "reliable": False,
                "verified": False,
                "summary": "Unverified at translation time. Run both snippets in the Execution Console below to verify behavioral equivalence."
            }
        },
        "breakdown": {
            "source_structure": src_struct,
            "target_structure": tgt_struct,
            "identifiers_source_count": len(src_ids),
            "identifiers_retained_count": len(retained_ids),
            "strings_source_count": len(src_strings),
            "strings_retained_count": len(retained_strings),
            "comments_source_count": len(src_comments),
            "comments_target_count": len(tgt_comments),
            "warning_count": len(warnings)
        },
        "know_how": {
            "structural_explanation": (
                f"We compared code construct counts between {source_lang} and {target_lang}: "
                f"Functions: {src_struct['functions']} -> {tgt_struct['functions']}, "
                f"Loops: {src_struct['loops']} -> {tgt_struct['loops']}, "
                f"Branches: {src_struct['branches']} -> {tgt_struct['branches']}, "
                f"Returns: {src_struct['returns']} -> {tgt_struct['returns']}."
            ),
            "content_explanation": (
                f"We tracked user-authored tokens: {len(retained_ids)} of {len(src_ids)} identifiers retained "
                f"across naming conventions (snake_case/camelCase), {len(retained_strings)} of {len(src_strings)} "
                f"string literals preserved, and {len(tgt_comments)} comments retained."
            ),
            "semantic_explanation": (
                "Semantic fidelity is a static estimation combining structural symmetry and identifier fidelity, "
                f"adjusted by {len(warnings)} diagnostic warning(s). Static analysis alone cannot prove identical program behavior."
            ),
            "what_was_not_verified": [
                "Runtime execution outputs under arbitrary user inputs",
                "Language-specific floating-point or integer division nuances",
                "Asynchronous event loop and promise resolution timing",
                "Exception handling behaviors for undeclared error types"
            ],
            "why_preservation_is_not_guarantee": (
                "Two programs can have identical 100% structural preservation (same number of functions, loops, and variables) "
                "yet produce different results if language semantics differ (such as Python's integer division '//' vs JavaScript's '/' or 0-indexing edge cases). "
                "Always run test inputs in the Execution Console below to verify actual runtime behavior."
            )
        }
    }
